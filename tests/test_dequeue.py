from __future__ import annotations

from taskqueue import dequeue, enqueue


def test_dequeue_empty_returns_none(conn):
    assert dequeue(conn, worker_id="w1") is None


def test_dequeue_returns_highest_priority(conn):
    enqueue(conn, idempotency_key="low", job_type="t", payload={}, priority=1)
    high_id = enqueue(conn, idempotency_key="high", job_type="t", payload={}, priority=10)
    enqueue(conn, idempotency_key="mid", job_type="t", payload={}, priority=5)

    job = dequeue(conn, worker_id="w1")
    assert job is not None
    assert job.id == high_id
    assert job.status == "running"
    assert job.worker_id == "w1"
    assert job.attempt_count == 1
    assert job.lease_expires_at is not None
    assert job.started_at is not None


def test_dequeue_fifo_within_same_priority(conn):
    first = enqueue(conn, idempotency_key="a", job_type="t", payload={}, priority=0)
    enqueue(conn, idempotency_key="b", job_type="t", payload={}, priority=0)
    job = dequeue(conn, worker_id="w1")
    assert job is not None and job.id == first


def test_dequeue_skips_future_retry_after(conn):
    enqueue(conn, idempotency_key="future", job_type="t", payload={}, priority=10)
    available_id = enqueue(conn, idempotency_key="now", job_type="t", payload={}, priority=1)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET retry_after = now() + interval '1 hour' WHERE idempotency_key = 'future'"
        )
    conn.commit()

    job = dequeue(conn, worker_id="w1")
    assert job is not None and job.id == available_id


def test_dequeue_returns_none_when_only_future_jobs(conn):
    enqueue(conn, idempotency_key="future", job_type="t", payload={})
    with conn.cursor() as cur:
        cur.execute("UPDATE jobs SET retry_after = now() + interval '1 hour'")
    conn.commit()
    assert dequeue(conn, worker_id="w1") is None
