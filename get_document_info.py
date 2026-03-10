import sys
import logging
from prettytable import PrettyTable
from adobesign_client import get_document_info, get_access_token

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def display_as_table(data: dict):
    """Display dictionary data in a table format."""
    table = PrettyTable()
    table.field_names = ["Key", "Value"]

    for key, value in data.items():
        table.add_row([key, value])

    print(table)


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        log.error("Usage: python get_document_info.py <agreement_id> [output_format]")
        sys.exit(1)

    agreement_id = sys.argv[1]
    output_format = sys.argv[2].lower() if len(sys.argv) == 3 else "json"

    if output_format not in {"json", "table"}:
        log.error("Invalid output format. Use 'json' or 'table'.")
        sys.exit(1)

    try:
        # Obtain access token
        access_token = get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        # Fetch document information
        document_info = get_document_info(agreement_id, headers)

        if output_format == "table":
            display_as_table(document_info)
        else:
            log.info("Document Information (JSON): %s", document_info)

    except Exception as e:
        log.error("An error occurred: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
