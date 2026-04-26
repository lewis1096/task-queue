from __future__ import annotations

import uuid
from typing import Any

import psycopg
from psycopg import errors as pg_errors
from psycopg.rows import dict_row

from taskqueue.models import Job

NOTIFY_CHANNEL = "jobs_new"


class DuplicateJobError(Exception):
    """Raised when an idempotency_key already exists."""

    def __init__(self, idempotency_key: str):
        super().__init__(f"job with idempotency_key={idempotency_key!r} already exists")
        self.idempotency_key = idempotency_key


def enqueue(
    conn: psycopg.Connection,
    *,
    idempotency_key: str,
    job_type: str,
    payload: dict[str, Any],
    priority: int = 0,
    max_attempts: int = 3,
) -> uuid.UUID:
    """Insert a new queued job and NOTIFY listeners. Commits on success."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jobs (idempotency_key, job_type, payload, priority, max_attempts)
                VALUES (%s, %s, %s::jsonb, %s, %s)
                RETURNING id
                """,
                (idempotency_key, job_type, psycopg.types.json.Jsonb(payload), priority, max_attempts),
            )
            row = cur.fetchone()
            assert row is not None
            job_id: uuid.UUID = row[0]
            cur.execute("SELECT pg_notify(%s, %s)", (NOTIFY_CHANNEL, str(job_id)))
        conn.commit()
        return job_id
    except pg_errors.UniqueViolation as exc:
        conn.rollback()
        raise DuplicateJobError(idempotency_key) from exc


def dequeue(
    conn: psycopg.Connection,
    *,
    worker_id: str,
    lease_seconds: int = 60,
) -> Job | None:
    """Atomically claim the highest-priority eligible job. Commits on success."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            WITH claimed AS (
                SELECT id FROM jobs
                WHERE status = 'queued'
                  AND (retry_after IS NULL OR retry_after <= now())
                ORDER BY priority DESC, created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE jobs j
            SET status = 'running',
                worker_id = %s,
                lease_expires_at = now() + make_interval(secs => %s),
                started_at = now(),
                attempt_count = attempt_count + 1
            FROM claimed
            WHERE j.id = claimed.id
            RETURNING j.*
            """,
            (worker_id, lease_seconds),
        )
        row = cur.fetchone()
    conn.commit()
    if row is None:
        return None
    return Job(**row)
