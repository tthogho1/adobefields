# GitHub Copilot Instructions for this repository

Purpose
- Help Copilot generate suggestions that match this repository's conventions and intent.

Repository context
- Small Python utilities that interact with Adobe Sign: `adobe_list_templates.py`, `adobe_sign_field_updater.py`, and `adobesign_client.py`.
- Keep changes minimal, focused, and well-tested.

Environment Setup
- Always use virtual environments for Python projects.
- Create a venv with `python -m venv .venv`.
- Activate the venv with `source .venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows).
- In VS Code select the venv interpreter (Ctrl+Shift+P > Python: Select Interpreter).
- After activation install dependencies with `pip install -r requirements.txt`.
- Never use the global Python; add `.venv` to `.gitignore`.

Coding style
- Target modern Python (type hints encouraged).
- Use clear, descriptive function and variable names.
- Prefer small functions (single responsibility) and avoid deeply nested logic.
- Use `logging` for messages (do not add prints in library code).
- Use f-strings for formatting and `requests` (or the existing HTTP client) for network calls.

Testing and safety
- Add or update unit tests when changing behavior.
- Make network calls mockable; avoid hardcoding credentials or secrets.

Commits and PRs
- Commit message: short summary (imperative), optional one-line body, and references (e.g., "Fix: update field mapping for template X").
- PR description: explain intent, list changed files, and include test/verification steps.

How to prompt Copilot in this repo
- Provide the file path, function name, and a short description of intent.
  - Example: "In `adobesign_client.py`, implement `get_template_fields(template_id: str) -> dict` to return field metadata using the Adobe Sign API, with retries and type hints." 
- Prefer incremental suggestions: ask for a single function or helper rather than whole-file rewrites.

When rejecting suggestions
- If a suggestion introduces new dependencies, complex side-effects, or lacks tests, prefer manual implementation.

Contact
- If unsure about changes, open a PR and request a review describing the intended behavior.
