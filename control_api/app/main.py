from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.health import router as health_router
from app.api.runs import router as runs_router
from shared.db import check_database_ready
from shared.logging_utils import configure_logging
from shared.queue import check_redis_ready
from shared.settings import get_settings


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("control-api")

app = FastAPI(title="LangGraph Platform Control API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(agents_router)
app.include_router(runs_router)


@app.on_event("startup")
def check_supabase_config() -> None:
    issues = settings.database_config_issues()
    if issues:
        logger.error(
            "Supabase database configuration issues detected.",
            extra={"extra": {"issues": issues}},
        )
        return
    try:
        check_database_ready()
        check_redis_ready()
        logger.info("Startup dependency checks passed.")
    except Exception as exc:
        logger.error(
            "Startup dependency checks failed.",
            extra={"extra": {"error": str(exc)}},
        )
