import os
import importlib.util
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_BASE_URL: str = os.getenv(
    "API_BASE_URL", "https://secure.jp1.adobesign.com/api/rest/v6"
)


def get_access_token() -> str:
    """Obtain an access token by delegating to adobesign_client.get_access_token()."""
    client_path = Path(__file__).resolve().parent.parent / "adobesign_client.py"
    spec = importlib.util.spec_from_file_location("adobesign_client", str(client_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.get_access_token()
