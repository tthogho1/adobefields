import pytest
import responses

from acrobat_sign.client import AcrobatSignClient, AcrobatSignClientError
from acrobat_sign.service import AcrobatSignAgreementService

BASE_URL = "https://secure.jp1.adobesign.com/api/rest/v6"
TOKEN = "test-token"


def _make_client() -> AcrobatSignClient:
    return AcrobatSignClient(base_url=BASE_URL, access_token=TOKEN)


# ---------------------------------------------------------------------------
# Client-level tests
# ---------------------------------------------------------------------------


class TestAcrobatSignClient:
    def test_missing_token_raises(self):
        with pytest.raises(AcrobatSignClientError, match="access_token is required"):
            AcrobatSignClient(access_token=None)

    @responses.activate
    def test_list_agreements_success(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/agreements",
            json={
                "userAgreementList": [
                    {"id": "a1", "name": "Doc A", "status": "IN_PROCESS"},
                    {"id": "a2", "name": "Doc B", "status": "COMPLETED"},
                ]
            },
            status=200,
        )
        client = _make_client()
        summaries = client.list_agreements()
        assert len(summaries) == 2
        assert summaries[0].id == "a1"
        assert summaries[1].name == "Doc B"

    @responses.activate
    def test_list_agreements_empty(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/agreements",
            json={"userAgreementList": []},
            status=200,
        )
        client = _make_client()
        assert client.list_agreements() == []

    @responses.activate
    def test_get_agreement_success(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/agreements/a1",
            json={"id": "a1", "name": "Doc A", "status": "IN_PROCESS"},
            status=200,
        )
        client = _make_client()
        detail = client.get_agreement("a1")
        assert detail.id == "a1"
        assert detail.status == "IN_PROCESS"

    @responses.activate
    def test_api_error_raises(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/agreements",
            json={"message": "Unauthorized"},
            status=401,
        )
        client = _make_client()
        with pytest.raises(AcrobatSignClientError, match="API error: 401"):
            client.list_agreements()

    @responses.activate
    def test_api_500_raises(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/agreements/a1",
            body="Internal Server Error",
            status=500,
        )
        client = _make_client()
        with pytest.raises(AcrobatSignClientError, match="API error: 500"):
            client.get_agreement("a1")


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

AGREEMENTS_LIST = [
    {"id": "a1", "name": "Agreement 1", "status": "IN_PROCESS"},
    {"id": "a2", "name": "Agreement 2", "status": "CANCELLED"},
    {"id": "a3", "name": "Agreement 3", "status": "EXPIRED"},
    {"id": "a4", "name": "Agreement 4", "status": "COMPLETED"},
    {"id": "a5", "name": "Agreement 5", "status": "IN_PROCESS"},
]


def _register_full_scenario():
    """Register responses for list + detail for all 5 agreements."""
    responses.add(
        responses.GET,
        f"{BASE_URL}/agreements",
        json={"userAgreementList": AGREEMENTS_LIST},
        status=200,
    )
    for item in AGREEMENTS_LIST:
        responses.add(
            responses.GET,
            f"{BASE_URL}/agreements/{item['id']}",
            json=item,
            status=200,
        )


class TestAcrobatSignAgreementService:
    @responses.activate
    def test_filter_all_statuses(self):
        _register_full_scenario()
        service = AcrobatSignAgreementService(_make_client())
        result = service.filter_agreements_by_status(include_other=True)

        assert result.in_progress_count == 2
        assert result.canceled_count == 1
        assert result.expired_count == 1
        assert result.other_count == 1
        assert result.other[0].status == "COMPLETED"

    @responses.activate
    def test_exclude_canceled(self):
        _register_full_scenario()
        service = AcrobatSignAgreementService(_make_client())
        result = service.filter_agreements_by_status(
            include_canceled=False, include_other=False
        )

        assert result.in_progress_count == 2
        assert result.canceled_count == 0
        assert result.expired_count == 1
        assert result.other_count == 0

    @responses.activate
    def test_only_in_progress(self):
        _register_full_scenario()
        service = AcrobatSignAgreementService(_make_client())
        result = service.filter_agreements_by_status(
            include_in_progress=True,
            include_canceled=False,
            include_expired=False,
            include_other=False,
        )

        assert result.in_progress_count == 2
        assert result.canceled_count == 0
        assert result.expired_count == 0
        assert result.other_count == 0

    @responses.activate
    def test_empty_agreement_list(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/agreements",
            json={"userAgreementList": []},
            status=200,
        )
        service = AcrobatSignAgreementService(_make_client())
        result = service.filter_agreements_by_status()

        assert result.in_progress_count == 0
        assert result.canceled_count == 0
        assert result.expired_count == 0
        assert result.other_count == 0

    @responses.activate
    def test_case_insensitive_status(self):
        """Status normalization should handle mixed-case values."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/agreements",
            json={
                "userAgreementList": [
                    {"id": "a1", "name": "Doc", "status": "in_process"},
                    {"id": "a2", "name": "Doc2", "status": "Cancelled"},
                    {"id": "a3", "name": "Doc3", "status": "expired"},
                ]
            },
            status=200,
        )
        for aid, status in [
            ("a1", "in_process"),
            ("a2", "Cancelled"),
            ("a3", "expired"),
        ]:
            responses.add(
                responses.GET,
                f"{BASE_URL}/agreements/{aid}",
                json={"id": aid, "name": f"Doc {aid}", "status": status},
                status=200,
            )

        service = AcrobatSignAgreementService(_make_client())
        result = service.filter_agreements_by_status()

        assert result.in_progress_count == 1
        assert result.canceled_count == 1
        assert result.expired_count == 1

    @responses.activate
    def test_all_same_status(self):
        items = [
            {"id": f"a{i}", "name": f"Doc {i}", "status": "EXPIRED"} for i in range(3)
        ]
        responses.add(
            responses.GET,
            f"{BASE_URL}/agreements",
            json={"userAgreementList": items},
            status=200,
        )
        for item in items:
            responses.add(
                responses.GET,
                f"{BASE_URL}/agreements/{item['id']}",
                json=item,
                status=200,
            )

        service = AcrobatSignAgreementService(_make_client())
        result = service.filter_agreements_by_status()

        assert result.expired_count == 3
        assert result.in_progress_count == 0
        assert result.canceled_count == 0

    @responses.activate
    def test_agreement_ids_match(self):
        _register_full_scenario()
        service = AcrobatSignAgreementService(_make_client())
        result = service.filter_agreements_by_status(include_other=True)

        in_progress_ids = [a.id for a in result.in_progress]
        assert "a1" in in_progress_ids
        assert "a5" in in_progress_ids
        assert result.canceled[0].id == "a2"
        assert result.expired[0].id == "a3"
        assert result.other[0].id == "a4"
