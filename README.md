# Adobe Fields Utilities

Small utilities to interact with Adobe Sign library templates and update
form field alignments.

## Files

- `adobe_sign_field_updater.py` — updates form field `alignment` to `RIGHT` for
  specified field names in a library document.
- `adobesign_client.py` — HTTP client helpers for Adobe Sign (access token,
  fetch/put form fields, list library documents).
- `adobe_list_templates.py` — CLI script to list library/template IDs and names.
- `.env.example` — example environment variables.

## Prerequisites

- Python 3.8+ (3.13 tested)
- `requests` package

You can create and activate a virtual environment in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt  # if you add one, or `pip install requests`
```

## Environment

Copy `.env.example` to `.env` and fill in your credentials and endpoints.
The script expects the following variables in the environment:

- `REFRESH_TOKEN`
- `CLIENT_ID`
- `CLIENT_SECRET`
- `OAUTH_URL` (defaults are provided in `.env.example`)
- `API_BASE_URL` (defaults are provided in `.env.example`)

.env and the virtual environment directory are already ignored via `.gitignore`.

## Usage

### List templates (prints `id` and `name`):

```powershell
python adobefields\adobe_list_templates.py
# JSON output:
python adobefields\adobe_list_templates.py -j
```

### Get document information:

Fetch document information for a specified agreement ID. The script supports two output formats: `json` (default) and `table`.

```powershell
python adobefields\get_document_info.py <agreement_id> [output_format]

# Example usage:
python adobefields\get_document_info.py CBJCHBCAABAAQ37v2FBrQUAhVHMVMPvP-oMPpEQiFthU
python adobefields\get_document_info.py CBJCHBCAABAAQ37v2FBrQUAhVHMVMPvP-oMPpEQiFthU table
```

Update field alignments:

```powershell
python adobefields\adobe_sign_field_updater.py <LIBRARY_ID> <FIELD_FILE>
# Example: python adobefields\adobe_sign_field_updater.py CBJ... field_names.txt
```

`<FIELD_FILE>` should contain one field name per line. The script will save a
modified file `changed_<LIBRARY_ID>.json` before sending the update.

## Notes

- Secrets in `.env` should not be committed — `.gitignore` ignores `.env`.
- If you want CI or packaging, add `requirements.txt` or `pyproject.toml`.

## License

Add a license file if you plan to publish this repository.

## Delete a library/template (new)

`adobe_delete_template.py` removes a library/template (libraryDocument) from
Adobe Sign. It reuses the OAuth helper in `adobesign_client.py` to obtain an
access token.

Environment (required): `REFRESH_TOKEN`, `CLIENT_ID`, `CLIENT_SECRET`,
`OAUTH_URL`.

URL configuration options:
- `API_BASE_URL` (recommended): full base URL including `/api/rest/vX`.
- or set `API_HOST` and `API_VERSION` (defaults: `https://secure.na1.adobesign.com`, `v5`).

Examples (PowerShell):

```powershell
$env:API_BASE_URL='https://secure.na1.adobesign.com/api/rest/v5'
python .\adobe_delete_template.py <library_id> -v
```

```powershell
$env:API_HOST='https://secure.na1.adobesign.com'
$env:API_VERSION='v5'
python .\adobe_delete_template.py <library_id>
```

Example (bash):

```bash
export API_BASE_URL='https://secure.na1.adobesign.com/api/rest/v5'
python3 adobe_delete_template.py <library_id>
```

Behavior: prints success for HTTP 200/202/204; exits non-zero on error.
