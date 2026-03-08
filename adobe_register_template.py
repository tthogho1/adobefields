#!/usr/bin/env python3
"""Register a PDF as an Adobe Sign library/template.

This script uses helper functions from `adobesign_client.py`:
- `get_access_token()` to obtain an OAuth access token
- `pdf_template_upload()` to upload a transient document
- `pdf_register_template()` to create the library/template entry

Example:
  python adobe_register_template.py path/to/doc.pdf "My Template Name"

Optional flags allow controlling sharing and template state.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

from adobesign_client import (
    get_access_token,
    pdf_template_upload,
    pdf_register_template,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Upload PDF and register as Adobe Sign template")
    p.add_argument("file", help="Path to PDF file to upload")
    p.add_argument("name", nargs="?", default=None, help="Template name to register (optional). If omitted, filename-YYYYMMDD will be used")
    p.add_argument("--sharing-mode", choices=("ACCOUNT", "GROUP"), default="ACCOUNT", help="Sharing mode for template")
    p.add_argument("--state", choices=("ACTIVE", "DRAFT", "AUTHORING"), default="ACTIVE", help="Template state")
    p.add_argument("--template-types", default="DOCUMENT", help="Comma-separated template types (default: DOCUMENT)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    log = logging.getLogger(__name__)

    path = Path(args.file)
    if not path.exists():
        log.error("File not found: %s", args.file)
        sys.exit(1)

    # If name not provided, build default from filename and today's date
    if not args.name:
        today = date.today().strftime("%Y%m%d")
        default_name = f"{path.stem}-{today}"
        args.name = default_name

    # 1. Obtain access token
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload transient document
    upload_resp = pdf_template_upload(str(path), headers)
    transient_id = upload_resp.get("transientDocumentId") or upload_resp.get("transientDocumentId")
    if not transient_id:
        log.error("transientDocumentId not returned: %s", upload_resp)
        sys.exit(1)
    log.info("Transient document id: %s", transient_id)

    # 3. Register template
    template_types = [t.strip() for t in args.template_types.split(",") if t.strip()]
    register_resp = pdf_register_template(
        transient_document_id=transient_id,
        name=args.name,
        headers=headers,
        sharing_mode=args.sharing_mode,
        state=args.state,
        template_types=template_types,
    )

    # 4. Output result
    print(json.dumps(register_resp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
