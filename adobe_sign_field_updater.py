import argparse
import json
import logging
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

import requests
import importlib.util
from copy import deepcopy


# ── Configuration values (read from environment; populate .env as needed)
load_dotenv()
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
OAUTH_URL = os.getenv("OAUTH_URL")
API_BASE_URL = os.getenv("API_BASE_URL")

# Load request functions from local adobesign_client.py (keeps imports working
# whether package or script is executed directly).
_client_path = Path(__file__).with_name("adobesign_client.py")
spec = importlib.util.spec_from_file_location("adobesign_client", str(_client_path))
adobe_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adobe_client)
get_access_token = adobe_client.get_access_token
fetch_form_fields = adobe_client.fetch_form_fields
put_form_fields = adobe_client.put_form_fields

# ── Logger configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# Request functions are provided by adobesign_client.py and loaded above.


# Static signature field to append when updating fields
SIGNATURE_FIELD = {
    "backgroundColor": "",
    "borderColor": "",
    "borderStyle": "SOLID",
    "borderWidth": -1.0,
    "displayLabel": "",
    "visible": True,
    "inputType": "SIGNATURE",
    "tooltip": "",
    "fontColor": "#000000",
    "fontName": "Helvetica",
    "fontSize": -1.0,
    "alignment": "LEFT",
    "displayFormat": "",
    "displayFormatType": "DEFAULT",
    "masked": False,
    "maskingText": "*",
    "radioCheckType": "CIRCLE",
    "conditionalAction": {"anyOrAll": "ANY", "action": "SHOW"},
    "contentType": "SIGNATURE",
    "defaultValue": "",
    "readOnly": False,
    "valueExpression": "",
    "calculated": False,
    "urlOverridable": False,
    "required": True,
    "minLength": -1,
    "maxLength": -1,
    "minValue": -1.0,
    "maxValue": -1.0,
    "validationErrMsg": "",
    "validation": "NONE",
    "currency": "",
    "origin": "AUTHORED",
    "signerIndex": 0,
    "name": "署名フィールド 1",
    "locations": [
        {
            "pageNumber": 1,
            "top": 150.84399693806972,
            "left": 31.57199935913086,
            "width": 172.87920018513998,
            "height": 36.0,
        }
    ],
    "assignee": "recipient0",
}


def read_field_names(field_file: str) -> list[str]:
    """Read a file containing one field name per line and return the list."""
    path = Path(field_file)
    if not path.exists():
        log.error("Field file not found: %s", field_file)
        sys.exit(1)
    names = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    log.info("Read %d field names from %s", len(names), field_file)
    return names


def update_alignments(
    data: dict, target_names: list[str], add_signature: bool = True
) -> tuple[dict, int]:
    """
    For every field in data["fields"] whose `name` is in `target_names`,
    set its `alignment` to "RIGHT". Return the modified data and the
    number of fields updated.
    """
    fields = data.get("fields", [])
    found_set: set[str] = set()
    updated = 0

    for field in fields:
        if field.get("name") in target_names:
            field["alignment"] = "RIGHT"
            found_set.add(field["name"])
            updated += 1

    # Warn about fields that were not found
    for name in target_names:
        if name not in found_set:
            log.warning("Field '%s' not found in document", name)

    log.info("Updated %d/%d fields alignment to RIGHT", updated, len(target_names))
    # Optionally add a signature field if not already present
    if add_signature:
        fields_list = data.setdefault("fields", [])
        exists = any(f.get("name") == SIGNATURE_FIELD.get("name") for f in fields_list)
        if not exists:
            fields_list.append(deepcopy(SIGNATURE_FIELD))
            log.info(
                "Appended signature field '%s' to fields", SIGNATURE_FIELD.get("name")
            )
        else:
            log.info(
                "Signature field '%s' already present, skipping append",
                SIGNATURE_FIELD.get("name"),
            )

    return data, updated


# put_form_fields is provided by adobesign_client.py


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adobe Sign Form Field Alignment Updater"
    )
    parser.add_argument("library_id", help="Library Document ID")
    parser.add_argument("field_file", help="Field names file (one per line)")
    args = parser.parse_args()

    # 1. Obtain access token
    access_token = get_access_token()
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Fetch form fields
    data = fetch_form_fields(args.library_id, auth_headers)

    # 3. Read field list
    target_names = read_field_names(args.field_file)
    if not target_names:
        log.info("Field file is empty — nothing to update. Exiting.")
        return

    # 4. Update alignment
    data, updated_count = update_alignments(data, target_names)

    # 5. Save modified JSON
    changed_path = Path(f"changed_{args.library_id}.json")
    changed_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Saved modified fields to %s", changed_path)

    # 6. Send updated fields with PUT
    put_form_fields(args.library_id, data, auth_headers)


if __name__ == "__main__":
    main()
