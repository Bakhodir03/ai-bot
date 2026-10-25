"""Local maintenance commands for the Telegram AI helper."""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATABASE_PATH, ROOT
from storage import initialize, purge_expired_data


def backup_database(destination: Path) -> Path:
    if destination.exists():
        raise FileExistsError(f"Backup already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as source, sqlite3.connect(destination) as target:
        source.backup(target)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram AI helper maintenance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prune", help="Remove local content past the retention period")
    backup = subparsers.add_parser("backup", help="Create a consistent SQLite backup")
    backup.add_argument("--output", type=Path, help="Destination .sqlite3 file")
    args = parser.parse_args()

    initialize()
    if args.command == "prune":
        from config import DATA_RETENTION_DAYS
        purge_expired_data(DATA_RETENTION_DAYS)
        print(f"Old local content removed using {DATA_RETENTION_DAYS}-day retention.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = args.output or ROOT / "backups" / f"telegram-ai-{stamp}.sqlite3"
    print(backup_database(output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
