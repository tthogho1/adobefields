import os
import sys
import json
import logging
from pathlib import Path

import requests

log = logging.getLogger(__name__)
from dotenv import load_dotenv

# Load .env values into environment early
load_dotenv()


def get_access_token() -> str:
    """Obtain an access token using the refresh token."""
    REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    OAUTH_URL = os.getenv("OAUTH_URL")

    resp = requests.post(
        OAUTH_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    if resp.status_code != 200:
        log.error("Token request failed (HTTP %s): %s", resp.status_code, resp.text)
        sys.exit(1)
    token = resp.json().get("access_token")
    if not token:
        log.error("access_token not found in response: %s", resp.text)
        sys.exit(1)
    log.info("Access token acquired successfully")
    return token


def fetch_form_fields(library_id: str, headers: dict) -> dict:
    """GET libraryDocuments/{library_id}/formFields and return the parsed JSON."""
    API_BASE_URL = os.getenv("API_BASE_URL")
    url = f"{API_BASE_URL}/libraryDocuments/{library_id}/formFields"
    # Debug: print the library_id before making the request
    print(f"library_id: {library_id}")
    resp = requests.get(url, headers=headers)
    if resp.status_code == 401:
        log.error("Unauthorized (HTTP 401): access token is invalid or expired")
        sys.exit(1)
    if resp.status_code != 200:
        log.error("GET formFields failed (HTTP %s): %s", resp.status_code, resp.text)
        sys.exit(1)

    data = resp.json()
    out_path = Path(f"{library_id}.json")
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Loaded form fields from %s  →  saved to %s", library_id, out_path)
    return data


def put_form_fields(library_id: str, data: dict, headers: dict) -> None:
    """PUT the modified fields JSON back to the Adobe Sign API."""
    API_BASE_URL = os.getenv("API_BASE_URL")
    url = f"{API_BASE_URL}/libraryDocuments/{library_id}/formFields"
    resp = requests.put(
        url,
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps(data, ensure_ascii=False),
    )

    status = resp.status_code
    if status == 200:
        log.info("PUT update completed successfully (HTTP 200)")
    elif status == 401:
        log.error("Unauthorized (HTTP 401): access token is invalid or expired")
        sys.exit(1)
    elif status == 409:
        log.error("Conflict (HTTP 409): resource conflict — %s", resp.text)
        sys.exit(1)
    else:
        log.error("PUT formFields failed (HTTP %s): %s", status, resp.text)
        sys.exit(1)


def list_library_documents(headers: dict) -> list[dict]:
    """Return a list of library/template documents with `id` and `name`.

    Expect the API response to contain a top-level `libraryDocumentList`
    array where each item includes `id` and `name` fields. Extra
    response-shape handling has been removed for clarity.
    """
    API_BASE_URL = os.getenv("API_BASE_URL")
    url = f"{API_BASE_URL}/libraryDocuments"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 401:
        log.error("Unauthorized (HTTP 401): access token is invalid or expired")
        sys.exit(1)
    if resp.status_code != 200:
        log.error(
            "GET libraryDocuments failed (HTTP %s): %s", resp.status_code, resp.text
        )
        sys.exit(1)

    data = resp.json()
    items = data.get("libraryDocumentList", []) if isinstance(data, dict) else []

    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        id_ = item.get("id")
        name = item.get("name")
        if id_ and name:
            out.append({"id": id_, "name": name})

    log.info("Found %d library documents", len(out))
    return out


def pdf_template_upload(file_path: str, headers: dict) -> dict:
    """Upload a PDF to the Adobe Sign `transientDocuments` endpoint.

    Returns the JSON response (including `transientDocumentId`) on success.
    The caller should provide `headers` containing an Authorization bearer token.
    """
    API_BASE_URL = os.getenv("API_BASE_URL")
    url = f"{API_BASE_URL}/transientDocuments"

    p = Path(file_path)
    if not p.exists():
        log.error("File not found: %s", file_path)
        sys.exit(1)

    log.info("Uploading transient document: %s", file_path)
    with p.open("rb") as fh:
        files = {"File": (p.name, fh, "application/pdf")}
        data = {"File-Name": p.name, "Mime-Type": "application/pdf"}
        resp = requests.post(url, headers=headers, files=files, data=data)

    if resp.status_code not in (200, 201):
        log.error(
            "Transient document upload failed (HTTP %s): %s",
            resp.status_code,
            resp.text,
        )
        sys.exit(1)

    try:
        return resp.json()
    except Exception:
        log.error("Failed to parse JSON response from transient upload: %s", resp.text)
        sys.exit(1)


def pdf_register_template(
    transient_document_id: str,
    name: str,
    headers: dict,
    *,
    sharing_mode: str = "ACCOUNT",
    state: str = "ACTIVE",
    template_types: list[str] | None = None,
) -> dict:
    """Register a transient document as a library/template.

    Parameters:
    - `transient_document_id`: the transientDocumentId returned from `pdf_template_upload`.
    - `name`: the template name provided by the user.
    - `headers`: headers dict including Authorization bearer token.
    - `sharing_mode`: one of "ACCOUNT" or "GROUP" (default "ACCOUNT").
    - `state`: one of "ACTIVE", "DRAFT", "AUTHORING" (default "ACTIVE").
    - `template_types`: list of template types (default ["DOCUMENT"]).

    Returns the parsed JSON response on success.
    """
    API_BASE_URL = os.getenv("API_BASE_URL")
    url = f"{API_BASE_URL}/libraryDocuments"

    if template_types is None:
        template_types = ["DOCUMENT"]

    body = {
        "fileInfos": [{"transientDocumentId": transient_document_id}],
        "name": name,
        "sharingMode": sharing_mode,
        "state": state,
        "templateTypes": template_types,
    }

    log.info(
        "Registering template '%s' from transient document %s",
        name,
        transient_document_id,
    )
    resp = requests.post(
        url, headers={**headers, "Content-Type": "application/json"}, json=body
    )

    if resp.status_code not in (200, 201):
        log.error("Register template failed (HTTP %s): %s", resp.status_code, resp.text)
        sys.exit(1)

    try:
        return resp.json()
    except Exception:
        log.error("Failed to parse JSON response from register template: %s", resp.text)
        sys.exit(1)


def get_document_info(agreement_id: str, headers: dict) -> dict:
    """Fetch document JSON information for a specified agreement ID using Adobe Sign API.

    Parameters:
    - `agreement_id`: The ID of the agreement to fetch information for.
    - `headers`: Headers dict including Authorization bearer token.

    Returns the parsed JSON response on success.
    """
    API_BASE_URL = os.getenv("API_BASE_URL")
    url = f"{API_BASE_URL}/agreements/{agreement_id}"

    log.info("Fetching document information for agreement ID: %s", agreement_id)
    resp = requests.get(url, headers=headers)

    if resp.status_code == 401:
        log.error("Unauthorized (HTTP 401): access token is invalid or expired")
        sys.exit(1)
    if resp.status_code != 200:
        log.error(
            "GET document information failed (HTTP %s): %s", resp.status_code, resp.text
        )
        sys.exit(1)

    try:
        return resp.json()
    except Exception:
        log.error(
            "Failed to parse JSON response from document information: %s", resp.text
        )
        sys.exit(1)
