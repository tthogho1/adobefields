import argparse
import json
import logging
import os
import sys
from pathlib import Path

import requests

from adobesign_client import get_access_token


log = logging.getLogger(__name__)


def load_agreement(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        log.error("Agreement file not found: %s", path)
        sys.exit(1)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        log.error("Failed to parse agreement JSON: %s", e)
        sys.exit(1)


def replace_library_id(agreement: dict, library_id: str) -> dict:
    # Update every fileInfo that contains libraryDocumentId
    if not isinstance(agreement.get("fileInfos"), list):
        log.error("Agreement JSON has no fileInfos list")
        sys.exit(1)

    replaced = False
    for fi in agreement["fileInfos"]:
        if isinstance(fi, dict) and "libraryDocumentId" in fi:
            fi["libraryDocumentId"] = library_id
            replaced = True

    if not replaced:
        # If no libraryDocumentId found, append one
        agreement.setdefault("fileInfos", []).append({"libraryDocumentId": library_id})
    return agreement


def post_agreement(agreement: dict, token: str, api_base: str) -> dict:
    url = f"{api_base.rstrip('/')}/agreements"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=agreement)
    try:
        data = resp.json()
    except Exception:
        data = {"status_code": resp.status_code, "text": resp.text}

    if resp.status_code not in (200, 201):
        log.error(
            "Agreement creation failed (HTTP %s): %s", resp.status_code, resp.text
        )
        return {"success": False, "response": data}

    return {"success": True, "response": data}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an Adobe Sign agreement from a JSON template"
    )
    parser.add_argument(
        "--library-id",
        required=True,
        help="Library document ID to insert into the agreement",
    )
    parser.add_argument(
        "--agreement-file",
        default="Agreement.json",
        help="Path to Agreement.json template",
    )
    parser.add_argument(
        "--api-base",
        default=os.getenv("API_BASE_URL", "https://api.jp1.adobesign.com/api/rest/v6"),
        help="Adobe Sign API base URL",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Load and modify the agreement JSON
    agreement = load_agreement(args.agreement_file)
    modified = replace_library_id(agreement, args.library_id)

    # Acquire access token (function exits on failure)
    token = get_access_token()

    result = post_agreement(modified, token, args.api_base)
    if not result.get("success"):
        print("Agreement creation failed:")
        print(json.dumps(result.get("response"), ensure_ascii=False, indent=2))
        return 1

    resp = result.get("response")
    # Print summary
    print("Agreement created successfully.")
    # Adobe Sign usually returns an `id` or `agreementId` — print whatever exists.
    for key in (
        "id",
        "agreementId",
        "agreementIdList",
    ):
        if isinstance(resp, dict) and key in resp:
            print(f"{key}: {resp[key]}")
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
