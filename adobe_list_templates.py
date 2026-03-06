import argparse
import json
import logging
import sys
from pathlib import Path
import os
import importlib.util


def load_env(path: str = ".env") -> None:
    """A minimal .env parser (ignore comments and blank lines)."""
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        os.environ.setdefault(key, val)


def load_client_module():
    _client_path = Path(__file__).with_name("adobesign_client.py")
    spec = importlib.util.spec_from_file_location("adobesign_client", str(_client_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List Adobe Sign library/template documents"
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    log = logging.getLogger(__name__)

    load_env()
    client = load_client_module()

    token = client.get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    templates = client.list_library_documents(headers)

    if args.json:
        print(json.dumps(templates, ensure_ascii=False, indent=2))
        return

    if not templates:
        log.info("No library documents found")
        return

    for t in templates:
        print(t.get("id"), "\t", t.get("name"))


if __name__ == "__main__":
    main()
