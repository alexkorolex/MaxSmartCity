"""Run with `python -m src.domains.ingestion FILE.json`."""

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from src.domains.ingestion.importer import import_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Import houses and reference organizations")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    load_dotenv()
    print(json.dumps(asyncio.run(import_file(args.file)), ensure_ascii=False))


if __name__ == "__main__":
    main()
