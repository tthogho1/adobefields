#!/usr/bin/env python3
"""Fetch form fields for a library/template and save as JSON.

Usage:
  python adobesign_get_fields.py --library-id LIB_ID [--output out.json]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from adobesign_client import get_access_token, fetch_form_fields

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch Adobe Sign library/template form fields and save JSON"
    )
    p.add_argument("--library-id", required=True, help="Library Document ID to fetch")
    p.add_argument(
        "--output", help="Output JSON file path (default: <library-id>.json)"
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    try:
        token = get_access_token()
    except SystemExit:
        log.error("Failed to obtain access token")
        return 2

    headers = {"Authorization": f"Bearer {token}"}

    try:
        data = fetch_form_fields(args.library_id, headers)
    except SystemExit:
        log.error("Failed to fetch form fields for %s", args.library_id)
        return 3

    out_path = Path(args.output) if args.output else Path(f"{args.library_id}.json")
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Saved form fields to %s", out_path)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
