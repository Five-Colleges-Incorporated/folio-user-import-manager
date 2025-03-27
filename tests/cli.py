import argparse
from pathlib import Path
from urllib.parse import urlparse


def main() -> None:
    desc = "Initiates, monitors, and reports on mod-user-import operations in FOLIO"
    parser = argparse.ArgumentParser(prog="fuiman", description=desc)
    parser.add_argument(
        "-e",
        "--folio-endpoint",
        type=urlparse,
    )
    parser.add_argument(
        "-t",
        "--folio-tenant",
    )
    parser.add_argument(
        "-u",
        "--folio-username",
    )
    parser.add_argument("-p", "--ask-folio-password", action="store_true")
    parser.add_argument(
        "data",
        type=Path,
        required=True,
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    args = parser.parse_args()


if __name__ == "main":
    main()
