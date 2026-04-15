#!/usr/bin/env python3
"""Delete an Adobe Sign library/template document.

Builds the API URL from a base host and version (or uses existing
`API_BASE_URL` env for backward compatibility) and uses
`get_access_token()` from `adobesign_client.py` to authenticate.

Usage:
  python adobe_delete_template.py <libraryDocumentId>

Environment variables:
  - API_BASE_URL (optional): full base URL including any path (e.g. https://.../api/rest/v5)
  - API_HOST (optional): host-only base (default: https://secure.na1.adobesign.com)
  - API_VERSION (optional): API version segment (default: v5)
  - Other OAuth env vars used by `get_access_token()` in `adobesign_client.py`
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

import requests

from adobesign_client import get_access_token

log = logging.getLogger(__name__)


def build_library_url(library_id: str) -> str:
    """Construct the libraryDocuments URL.

    Priority:
    1. Use `API_BASE_URL` if set (keeps existing behavior elsewhere).
    2. Otherwise build from `API_HOST` + `/api/rest/{API_VERSION}`.
    """
    # api_base = os.getenv("API_BASE_URL")
    # if api_base:
    #    return f"{api_base.rstrip('/')}/libraryDocuments/{library_id}"

    api_host = os.getenv("API_HOST", "https://secure.jp1.adobesign.com")
    api_version = os.getenv("API_VERSION", "v5")
    return (
        f"{api_host.rstrip('/')}/api/rest/{api_version}/libraryDocuments/{library_id}"
    )


def delete_library_document(library_id: str) -> None:
    """Delete the specified library/template document.

    Exits with non-zero status on failure.
    """
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = build_library_url(library_id)
    log.info("DELETE %s", url)
    resp = requests.delete(url, headers=headers)

    if resp.status_code in (200, 202, 204):
        print(f"Deleted library document {library_id} (HTTP {resp.status_code})")
        return

    if resp.status_code == 401:
        log.error("Unauthorized (HTTP 401): access token invalid or expired")
        sys.exit(1)

    log.error(
        "DELETE libraryDocuments failed (HTTP %s): %s", resp.status_code, resp.text
    )
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete an Adobe Sign library/template document"
    )
    parser.add_argument("library_id", help="Library document id to delete")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    delete_library_document(args.library_id)


if __name__ == "__main__":
    main()
