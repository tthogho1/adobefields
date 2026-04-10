#!/usr/bin/env python3
"""CLI: List Acrobat Sign agreements by status.

Outputs either a human-friendly table (default) or JSON (`--json`).

This script uses `adobesign_client.get_access_token()` via
`acrobat_sign.config.get_access_token()` to obtain an OAuth access token.
"""
from __future__ import annotations

import argparse
import json
import logging
from typing import Optional

from prettytable import PrettyTable

from acrobat_sign.config import get_access_token
from acrobat_sign.client import AcrobatSignClient
from acrobat_sign.service import AcrobatSignAgreementService

log = logging.getLogger(__name__)


def render_table(result) -> None:
    def section(title: str, items: list):
        print(f"{title} ({len(items)}):")
        if not items:
            print("  (none)")
            return
        t = PrettyTable()
        t.field_names = ["ID", "Name", "Status"]
        for a in items:
            t.add_row([a.id, a.name or "", a.status])
        print(t)

    section("In progress", result.in_progress)
    section("Canceled", result.canceled)
    section("Expired", result.expired)
    section("Other", result.other)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="List Acrobat Sign agreements by status")
    p.add_argument(
        "--json", "-j", dest="as_json", action="store_true", help="Output JSON"
    )
    p.add_argument(
        "--user-id", dest="user_id", help="Optional userId to scope the list"
    )
    p.add_argument(
        "--workers",
        dest="workers",
        type=int,
        default=10,
        help="Concurrent workers for fetching details",
    )
    p.add_argument(
        "--include-other",
        dest="include_other",
        action="store_true",
        help="Include non-target statuses in 'Other'",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        log.info("Obtaining access token...")
        token = get_access_token()
        log.info("Access token obtained")
    except Exception as exc:  # pragma: no cover - integration path
        log.error("Failed to obtain access token: %s", exc)
        return 2

    client = AcrobatSignClient(access_token=token)
    svc = AcrobatSignAgreementService(client)

    log.info(
        "Starting agreement fetch (user_id=%s, workers=%d)", args.user_id, args.workers
    )
    result = svc.filter_agreements_by_status(
        user_id=args.user_id,
        include_other=args.include_other,
        max_workers=args.workers,
    )

    log.info(
        "Fetch complete: in_progress=%d canceled=%d expired=%d other=%d",
        len(result.in_progress),
        len(result.canceled),
        len(result.expired),
        len(result.other),
    )

    if args.as_json:
        # Use Pydantic model_dump() to get native types
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    else:
        render_table(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
import argparse
import json
import logging
import sys

from dotenv import load_dotenv
from prettytable import PrettyTable

from acrobat_sign.client import AcrobatSignClient, AcrobatSignClientError
from acrobat_sign.config import get_access_token
from acrobat_sign.service import AcrobatSignAgreementService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List Adobe Sign agreements grouped by status with counts"
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    log = logging.getLogger(__name__)

    load_dotenv()

    try:
        token = get_access_token()
        client = AcrobatSignClient(access_token=token)
        service = AcrobatSignAgreementService(client)

        result = service.filter_agreements_by_status(
            include_in_progress=True,
            include_canceled=True,
            include_expired=True,
            include_other=True,
        )
    except AcrobatSignClientError as exc:
        log.error("API error: %s", exc)
        sys.exit(1)

    if args.json:
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        return

    sections = [
        ("In Progress (IN_PROCESS)", result.in_progress, result.in_progress_count),
        ("Canceled (CANCELLED)", result.canceled, result.canceled_count),
        ("Expired (EXPIRED)", result.expired, result.expired_count),
        ("Other", result.other, result.other_count),
    ]

    for label, agreements, count in sections:
        print(f"\n{label}  —  count: {count}")
        if not agreements:
            print("  (none)")
            continue
        table = PrettyTable()
        table.field_names = ["Agreement ID", "Name", "Status"]
        table.align = "l"
        for a in agreements:
            table.add_row([a.id, a.name, a.status])
        print(table)


if __name__ == "__main__":
    main()
