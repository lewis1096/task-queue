"""Demo worker entry point — runs ``taskqueue.Worker`` with the demo handlers.

A real application would replace ``demo_service`` with its own package and
its own handler module; the wiring shown here is the entire footprint of
``taskqueue`` integration on the worker side.
"""

from __future__ import annotations

import logging
import os
import signal
import socket

import taskqueue

from demo_service.handlers import HANDLERS

logger = logging.getLogger(__name__)


def build_worker() -> taskqueue.Worker:
    """Construct the Worker from environment configuration.

    Split out from ``main`` so tests can build the same worker without
    triggering the signal-handler installation (signals only work in the
    main thread).
    """
    return taskqueue.Worker(
        handlers=HANDLERS,
        worker_id=os.environ.get("WORKER_ID", socket.gethostname()),
        concurrency=int(os.environ.get("WORKER_CONCURRENCY", "1")),
        lease_seconds=int(os.environ.get("LEASE_SECONDS", "60")),
        poll_interval=float(os.environ.get("POLL_INTERVAL_S", "5.0")),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    worker = build_worker()
    signal.signal(signal.SIGTERM, lambda *_: worker.stop())
    signal.signal(signal.SIGINT, lambda *_: worker.stop())
    logger.info(
        "demo worker starting: worker_id=%s concurrency=%d poll_interval=%.1fs",
        worker.worker_id,
        worker.concurrency,
        worker.poll_interval,
    )
    worker.run()
    logger.info("demo worker stopped cleanly")


if __name__ == "__main__":
    main()
