from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agents import router as agents_router
from app.api.health import router as health_router
from app.api.runs import router as runs_router
from shared.logging_utils import configure_logging
from shared.settings import get_settings


settings = get_settings()
configure_logging(settings.log_level)

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
