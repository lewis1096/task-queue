import os

import psycopg


def get_connection() -> psycopg.Connection:
    """Return a psycopg connection using DATABASE_URL from the environment."""
    dsn = os.environ["DATABASE_URL"]
    return psycopg.connect(dsn)
