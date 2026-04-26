from __future__ import annotations

import json

from redis import Redis

from shared.schemas import QueueJobEnvelope
from shared.settings import get_settings


settings = get_settings()


def get_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def check_redis_ready() -> None:
    client = get_redis_client()
    client.ping()


def enqueue_run_job(job: QueueJobEnvelope) -> None:
    client = get_redis_client()
    client.rpush(settings.queue_name, job.model_dump_json())


def pop_run_job(timeout_seconds: int) -> QueueJobEnvelope | None:
    client = get_redis_client()
    result = client.blpop(settings.queue_name, timeout=timeout_seconds)
    if result is None:
        return None
    _, payload = result
    data = json.loads(payload)
    return QueueJobEnvelope.model_validate(data)

