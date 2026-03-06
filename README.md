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

List templates (prints `id` and `name`):

```powershell
python adobefields\adobe_list_templates.py
# JSON output:
python adobefields\adobe_list_templates.py -j
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
