#!/usr/bin/env python3
"""
Migration helper script.

This script helps run Alembic migrations for the application.
Usage:
    python scripts/migrate.py upgrade    # Apply all pending migrations
    python scripts/migrate.py downgrade   # Rollback one migration
    python scripts/migrate.py current     # Show current migration version
    python scripts/migrate.py history     # Show migration history
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

load_dotenv()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate.py <command> [options]")
        print("\nCommands:")
        print("  upgrade [head|+N|-N]  - Apply migrations (default: head)")
        print("  downgrade [-N|revision] - Rollback migrations")
        print("  current              - Show current migration version")
        print("  history               - Show migration history")
        print("  stamp <revision>      - Mark database as being at a specific revision")
        print("  revision [-m message] - Create a new migration")
        sys.exit(1)

    cmd = sys.argv[1]
    alembic_cfg = Config(str(project_root / "alembic.ini"))

    if cmd == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        print(f"Upgrading database to: {revision}")
        command.upgrade(alembic_cfg, revision)
    elif cmd == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        print(f"Downgrading database by: {revision}")
        command.downgrade(alembic_cfg, revision)
    elif cmd == "current":
        command.current(alembic_cfg)
    elif cmd == "history":
        command.history(alembic_cfg)
    elif cmd == "stamp":
        if len(sys.argv) < 3:
            print("Usage: python scripts/migrate.py stamp <revision>")
            sys.exit(1)
        revision = sys.argv[2]
        print(f"Stamping database as: {revision}")
        command.stamp(alembic_cfg, revision)
    elif cmd == "revision":
        message = None
        autogenerate = False
        if "-m" in sys.argv:
            idx = sys.argv.index("-m")
            if idx + 1 < len(sys.argv):
                message = sys.argv[idx + 1]
        if "--autogenerate" in sys.argv or "-a" in sys.argv:
            autogenerate = True
        
        if autogenerate:
            if not message:
                print("Error: --autogenerate requires -m <message>")
                sys.exit(1)
            print(f"Creating auto-generated migration: {message}")
            command.revision(alembic_cfg, message=message, autogenerate=True)
        else:
            if message:
                print(f"Creating empty migration: {message}")
                command.revision(alembic_cfg, message=message)
            else:
                print("Creating empty migration (use -m <message> for description)")
                command.revision(alembic_cfg)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()

