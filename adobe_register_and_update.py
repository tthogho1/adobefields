#!/usr/bin/env python3
"""Register a PDF as an Adobe Sign template and then update form fields.

This composes the existing helpers in `adobesign_client.py` and the
field-update logic from `adobe_sign_field_updater.py` into one CLI.

Usage examples:
  python adobe_register_and_update.py path/to/doc.pdf "Template Name" --field-file fields.txt
  python adobe_register_and_update.py path/to/doc.pdf --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Tuple, List
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from adobesign_client import (
    get_access_token,
    pdf_template_upload,
    pdf_register_template,
    fetch_form_fields,
    put_form_fields,
)

# Reuse the same small helpers as in `adobe_sign_field_updater.py`.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def read_field_names(field_file: str) -> list[str]:
    p = Path(field_file)
    if not p.exists():
        log.error("Field file not found: %s", field_file)
        sys.exit(1)
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def update_alignments(data: dict, target_names: List[str]) -> Tuple[dict, int]:
    fields = data.get("fields", [])
    found_set: set[str] = set()
    updated = 0
    for field in fields:
        if field.get("name") in target_names:
            field["alignment"] = "RIGHT"
            found_set.add(field.get("name"))
            updated += 1
    for name in target_names:
        if name not in found_set:
            log.warning("Field '%s' not found in document", name)
    log.info("Updated %d/%d fields alignment to RIGHT", updated, len(target_names))
    return data, updated


def extract_transient_id(upload_resp: dict) -> str | None:
    return (
        upload_resp.get("transientDocumentId")
        or upload_resp.get("transient_document_id")
        or upload_resp.get("transientId")
    )


def extract_library_id(register_resp: dict) -> str | None:
    return (
        register_resp.get("id")
        or register_resp.get("libraryDocumentId")
        or register_resp.get("library_document_id")
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Register PDF and update Adobe Sign template fields"
    )
    p.add_argument("pdf", help="Path to PDF file to register")
    p.add_argument("name", nargs="?", default=None, help="Template name (optional)")
    p.add_argument(
        "--field-file", default="fields.txt", help="Field names file (one per line)"
    )
    p.add_argument("--sharing-mode", choices=("ACCOUNT", "GROUP"), default="ACCOUNT")
    p.add_argument(
        "--state", choices=("ACTIVE", "DRAFT", "AUTHORING"), default="ACTIVE"
    )
    p.add_argument(
        "--template-types", default="DOCUMENT", help="Comma-separated template types"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do everything except call PUT to update fields",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        log.error("PDF not found: %s", args.pdf)
        sys.exit(1)

    if not args.name:
        today = date.today().strftime("%Y%m%d")
        args.name = f"{pdf_path.stem}-{today}"

    # 1. Obtain access token
    try:
        token = get_access_token()
    except SystemExit:
        log.error("Failed to obtain access token")
        sys.exit(1)
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload transient document
    try:
        upload_resp = pdf_template_upload(str(pdf_path), headers)
    except SystemExit:
        log.error("Transient document upload failed")
        sys.exit(1)

    transient_id = extract_transient_id(upload_resp)
    if not transient_id:
        log.error("transientDocumentId not returned: %s", upload_resp)
        sys.exit(1)
    log.info("Transient document id: %s", transient_id)

    # 3. Register template
    template_types = [t.strip() for t in args.template_types.split(",") if t.strip()]
    try:
        register_resp = pdf_register_template(
            transient_document_id=transient_id,
            name=args.name,
            headers=headers,
            sharing_mode=args.sharing_mode,
            state=args.state,
            template_types=template_types,
        )
    except SystemExit:
        log.error("Register template failed")
        sys.exit(1)

    lib_id = extract_library_id(register_resp)
    if not lib_id:
        log.error(
            "No template/library id found in register response: %s", register_resp
        )
        print(json.dumps(register_resp, ensure_ascii=False, indent=2))
        sys.exit(1)
    log.info("Registered template id: %s", lib_id)

    # 4. Fetch form fields
    try:
        data = fetch_form_fields(lib_id, headers)
    except SystemExit:
        log.error("Failed to fetch form fields for %s", lib_id)
        sys.exit(1)

    # 5. Read field list and update
    target_names = read_field_names(args.field_file)
    if not target_names:
        log.info("Field file is empty — nothing to update. Exiting.")
        print(json.dumps(register_resp, ensure_ascii=False, indent=2))
        return

    data, updated_count = update_alignments(data, target_names)

    # 6. Save modified JSON
    changed_path = Path(f"changed_{lib_id}.json")
    changed_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Saved modified fields to %s", changed_path)

    # 7. PUT updated fields unless dry-run
    if args.dry_run:
        log.info("Dry-run: skipping PUT to Adobe Sign API")
    else:
        try:
            put_form_fields(lib_id, data, headers)
        except SystemExit:
            log.error("PUT update failed for %s", lib_id)
            sys.exit(1)

    # 8. Output register response
    print(json.dumps(register_resp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
