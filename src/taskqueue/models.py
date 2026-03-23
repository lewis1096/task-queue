from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Job:
    id: uuid.UUID
    idempotency_key: str
    job_type: str
    payload: dict[str, Any]
    priority: int = 0
    status: str = "queued"
    attempt_count: int = 0
    max_attempts: int = 3
    worker_id: str | None = None
    lease_expires_at: datetime | None = None
    retry_after: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_payload: dict[str, Any] | None = None
    error_message: str | None = None
