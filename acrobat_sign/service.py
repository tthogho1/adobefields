import concurrent.futures
import logging
from typing import Optional

from .client import AcrobatSignClient
from .models import AgreementFilterResult

log = logging.getLogger(__name__)


def _normalize_status(status: str) -> str:
    return status.upper().strip()


class AcrobatSignAgreementService:
    def __init__(self, client: AcrobatSignClient):
        self.client = client

    def filter_agreements_by_status(
        self,
        user_id: Optional[str] = None,
        include_in_progress: bool = True,
        include_canceled: bool = True,
        include_expired: bool = True,
        include_other: bool = False,
        *,
        max_workers: int = 10,
    ) -> AgreementFilterResult:
        """List agreements, fetch detail for each, and group by status.

        This implementation fetches agreement details concurrently using a
        thread pool (default 10 workers) to improve throughput when there are
        many agreements. Caller may adjust `max_workers` as needed.
        """
        summaries = self.client.list_agreements(user_id=user_id)
        log.info("Found %d agreements, fetching details…", len(summaries))

        result = AgreementFilterResult()

        if not summaries:
            return result

        log.info("Fetching agreement details concurrently with %d workers", max_workers)
        # Fetch details concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            future_to_id = {
                ex.submit(self.client.get_agreement, s.id): s.id for s in summaries
            }

            for fut in concurrent.futures.as_completed(future_to_id):
                aid = future_to_id[fut]
                try:
                    detail = fut.result()
                except Exception as exc:  # pragma: no cover - network/error path
                    log.error("Failed to fetch agreement %s: %s", aid, exc)
                    continue

                # Helpful debug log for each fetched agreement
                log.debug(
                    "Fetched agreement %s: status=%s",
                    aid,
                    getattr(detail, "status", None),
                )

                status = _normalize_status(detail.status)

                if status == "IN_PROCESS" and include_in_progress:
                    result.in_progress.append(detail)
                elif status == "CANCELLED" and include_canceled:
                    result.canceled.append(detail)
                elif status == "EXPIRED" and include_expired:
                    result.expired.append(detail)
                elif include_other:
                    result.other.append(detail)

        log.info(
            "Grouping complete: in_progress=%d canceled=%d expired=%d other=%d",
            len(result.in_progress),
            len(result.canceled),
            len(result.expired),
            len(result.other),
        )

        return result
