from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from shared.db import check_database_ready
from shared.queue import check_redis_ready


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "control-api", "ts": datetime.now(UTC).isoformat()}


@router.get("/ready")
def ready() -> dict:
    try:
        check_database_ready()
        check_redis_ready()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database not ready: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Dependency not ready: {exc}") from exc
    return {"status": "ready"}

