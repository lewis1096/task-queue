from __future__ import annotations

import threading
import uuid

from taskqueue import JobStatus, dequeue, enqueue


def test_concurrent_dequeue_no_double_claim(conn, make_conn):
    n_jobs = 20
    n_workers = 10

    for i in range(n_jobs):
        enqueue(conn, idempotency_key=f"k-{i}", job_type="t", payload={}, priority=0)

    barrier = threading.Barrier(n_workers)
    claims: list[uuid.UUID] = []
    claims_lock = threading.Lock()

    def worker(worker_id: str) -> None:
        c = make_conn()
        local: list[uuid.UUID] = []
        barrier.wait()
        while True:
            job = dequeue(c, worker_id=worker_id)
            if job is None:
                break
            local.append(job.id)
        with claims_lock:
            claims.extend(local)

    threads = [threading.Thread(target=worker, args=(f"w-{i}",)) for i in range(n_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        assert not t.is_alive(), "worker thread hung"

    assert len(claims) == n_jobs, f"expected {n_jobs} claims, got {len(claims)}"
    assert len(set(claims)) == n_jobs, "a job was claimed more than once"

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM jobs WHERE status = %s", (JobStatus.RUNNING,))
        assert cur.fetchone()[0] == n_jobs
