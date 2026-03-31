"""Run SQL migrations against the database.

Usage:
    ROLE=migrate  (via entrypoint.sh)
    python -m taskqueue.migrate  (directly)
"""

import os
import pathlib

from taskqueue.db import get_connection


def run_migrations() -> None:
    migration_dir = pathlib.Path(os.environ.get("MIGRATIONS_DIR", "migrations"))
    migration_files = sorted(migration_dir.glob("*.sql"))

    if not migration_files:
        print("No migration files found in", migration_dir)
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for migration_file in migration_files:
                print(f"Running {migration_file.name} ...")
                sql = migration_file.read_text()
                cur.execute(sql)
        conn.commit()
        print("All migrations applied successfully.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migrations()
