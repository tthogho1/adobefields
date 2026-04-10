import logging
from typing import Any

import requests

from .config import API_BASE_URL
from .models import AgreementSummary, AgreementDetail

log = logging.getLogger(__name__)


class AcrobatSignClientError(Exception):
    pass


class AcrobatSignClient:
    def __init__(
        self,
        base_url: str | None = None,
        access_token: str | None = None,
    ):
        self.base_url = (base_url or API_BASE_URL).rstrip("/")
        if not access_token:
            raise AcrobatSignClientError("access_token is required")
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = requests.request(method, url, headers=self.headers, **kwargs)
        if resp.status_code >= 400:
            raise AcrobatSignClientError(f"API error: {resp.status_code} {resp.text}")
        return resp.json()

    def list_agreements(self, user_id: str | None = None) -> list[AgreementSummary]:
        """GET /agreements — return high-level agreement summaries.

        This method attempts to handle paginated responses by requesting pages
        in a loop. The Acrobat Sign API uses cursor-based pagination and
        returns `page.nextCursor` (or `nextCursor`) when more pages are
        available. Older implementations that attempted to use `start`/`limit`
        don't work for that API and could cause infinite loops; this method
        explicitly uses `cursor` when provided by the service.
        """
        params: dict[str, object] = {}
        if user_id:
            params["userId"] = user_id

        page_size = 100
        cursor: str | None = None
        all_items: list[dict] = []

        while True:
            # Build request params for this page
            req_params = {**params, "limit": page_size}
            if cursor:
                req_params["cursor"] = cursor

            data = self._request("GET", "/agreements", params=req_params)

            # Normalize response shapes
            if isinstance(data, dict):
                raw_list = (
                    data.get("userAgreementList")
                    or data.get("agreementList")
                    or data.get("agreements")
                    or []
                )
                page = data.get("page") or {}
                cursor = page.get("nextCursor") or data.get("nextCursor")
            elif isinstance(data, list):
                raw_list = data
                cursor = None
            else:
                raw_list = []
                cursor = None

            if not raw_list:
                log.info("No agreements returned by API for params=%s", req_params)
                break

            all_items.extend(raw_list)
            log.info("Fetched %d agreements (params=%s)", len(raw_list), req_params)

            # If API didn't return a next cursor, we've reached the end
            if not cursor:
                break

        log.info("Total agreements fetched: %d", len(all_items))
        return [AgreementSummary.model_validate(item) for item in all_items]

    def get_agreement(self, agreement_id: str) -> AgreementDetail:
        """GET /agreements/{agreementId} — return detailed agreement info."""
        data = self._request("GET", f"/agreements/{agreement_id}")
        return AgreementDetail.model_validate(data)
