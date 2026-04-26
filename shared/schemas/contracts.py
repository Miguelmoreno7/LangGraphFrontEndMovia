from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    viewer = "viewer"
    operator = "operator"
    admin = "admin"


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class AgentToggleRequest(BaseModel):
    enabled: bool


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    name: str
    enabled: bool
    default_version: str | None
    created_at: datetime
    updated_at: datetime


class AgentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    version: str
    entrypoint: str
    config_json: dict
    status: str
    created_at: datetime


class RunCreateRequest(BaseModel):
    agent_id: UUID
    version: str | None = None
    input: dict = Field(default_factory=dict)
    requested_by: str | None = None


class QueueJobEnvelope(BaseModel):
    run_id: UUID
    agent_id: UUID
    version: str
    enqueued_at: datetime
    attempts: int = 0


class RunListItem(BaseModel):
    id: UUID
    status: RunStatus
    agent_id: UUID
    agent_key: str
    agent_name: str
    version: str
    requested_by: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_text: str | None


class RunDetailResponse(BaseModel):
    id: UUID
    status: RunStatus
    agent_id: UUID
    agent_version_id: UUID
    version: str
    input_json: dict
    output_json: dict | None
    error_text: str | None
    requested_by: str | None
    attempt_count: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class RunEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: UUID
    ts: datetime
    level: str
    event_type: str
    message: str
    payload_json: dict

