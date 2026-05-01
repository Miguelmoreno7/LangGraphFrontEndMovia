from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from app.deps import RequestContext, require_roles
from shared.db import Agent, AgentVersion, Run, RunEvent, get_db_session
from shared.queue import enqueue_run_job
from shared.schemas import (
    QueueJobEnvelope,
    Role,
    RunCreateRequest,
    RunDetailResponse,
    RunEventResponse,
    RunListItem,
    RunStatus,
)


router = APIRouter(prefix="/runs", tags=["runs"])


def _resolve_version(session: Session, agent_id: UUID, requested_version: str | None) -> AgentVersion:
    filters = [AgentVersion.agent_id == agent_id]
    if requested_version:
        filters.append(AgentVersion.version == requested_version)
    version_query: Select[tuple[AgentVersion]] = (
        select(AgentVersion)
        .where(and_(*filters))
        .order_by(AgentVersion.created_at.desc())
    )
    version = session.scalars(version_query).first()
    if version is None:
        requested_label = requested_version or "default"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent version '{requested_label}' not found.",
        )
    return version


@router.post("", response_model=RunDetailResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    payload: RunCreateRequest,
    ctx: RequestContext = Depends(require_roles(Role.operator, Role.admin)),
    session: Session = Depends(get_db_session),
) -> RunDetailResponse:
    agent = session.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent is disabled. Enable agent before creating runs.",
        )

    requested_version = payload.version or agent.default_version
    version = _resolve_version(session, payload.agent_id, requested_version)
    now = datetime.now(UTC)

    run = Run(
        agent_id=agent.id,
        agent_version_id=version.id,
        status=RunStatus.queued.value,
        input_json=payload.input,
        requested_by=payload.requested_by or ctx.user,
        created_at=now,
    )
    session.add(run)
    session.flush()

    run_event = RunEvent(
        run_id=run.id,
        level="info",
        event_type="queue",
        message="Run queued by control API.",
        payload_json={
            "request_id": ctx.request_id,
            "requested_by": payload.requested_by or ctx.user,
            "version": version.version,
        },
    )
    session.add(run_event)
    session.commit()
    session.refresh(run)

    job = QueueJobEnvelope(
        run_id=run.id,
        agent_id=agent.id,
        version=version.version,
        enqueued_at=now,
    )
    try:
        enqueue_run_job(job)
    except Exception as exc:
        run.status = RunStatus.failed.value
        run.error_text = f"Queue enqueue failed: {exc}"
        run.finished_at = datetime.now(UTC)
        session.add(run)
        session.add(
            RunEvent(
                run_id=run.id,
                level="error",
                event_type="queue",
                message="Failed to enqueue run.",
                payload_json={"error": str(exc)},
            )
        )
        session.commit()
        raise HTTPException(status_code=503, detail="Queue unavailable. Run marked failed.") from exc

    return RunDetailResponse(
        id=run.id,
        status=RunStatus(run.status),
        agent_id=run.agent_id,
        agent_version_id=run.agent_version_id,
        version=version.version,
        input_json=run.input_json,
        output_json=run.output_json,
        error_text=run.error_text,
        total_tokens=run.total_tokens,
        total_duration_ms=run.total_duration_ms,
        requested_by=run.requested_by,
        attempt_count=run.attempt_count,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )


@router.get("", response_model=list[RunListItem])
def list_runs(
    agent_id: UUID | None = Query(default=None),
    status_filter: RunStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    _: RequestContext = Depends(require_roles(Role.viewer, Role.operator, Role.admin)),
    session: Session = Depends(get_db_session),
) -> list[RunListItem]:
    query = (
        select(Run, Agent, AgentVersion)
        .join(Agent, Run.agent_id == Agent.id)
        .join(AgentVersion, Run.agent_version_id == AgentVersion.id)
        .order_by(Run.created_at.desc())
        .limit(limit)
    )
    if agent_id is not None:
        query = query.where(Run.agent_id == agent_id)
    if status_filter is not None:
        query = query.where(Run.status == status_filter.value)

    items: list[RunListItem] = []
    for run, agent, version in session.execute(query).all():
        items.append(
            RunListItem(
                id=run.id,
                status=RunStatus(run.status),
                agent_id=agent.id,
                agent_key=agent.key,
                agent_name=agent.name,
                version=version.version,
                requested_by=run.requested_by,
                created_at=run.created_at,
                started_at=run.started_at,
                finished_at=run.finished_at,
                total_tokens=run.total_tokens,
                total_duration_ms=run.total_duration_ms,
                error_text=run.error_text,
            )
        )
    return items


@router.get("/{run_id}", response_model=RunDetailResponse)
def get_run(
    run_id: UUID,
    _: RequestContext = Depends(require_roles(Role.viewer, Role.operator, Role.admin)),
    session: Session = Depends(get_db_session),
) -> RunDetailResponse:
    query = (
        select(Run, AgentVersion)
        .join(AgentVersion, Run.agent_version_id == AgentVersion.id)
        .where(Run.id == run_id)
    )
    row = session.execute(query).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    run, version = row
    return RunDetailResponse(
        id=run.id,
        status=RunStatus(run.status),
        agent_id=run.agent_id,
        agent_version_id=run.agent_version_id,
        version=version.version,
        input_json=run.input_json,
        output_json=run.output_json,
        error_text=run.error_text,
        total_tokens=run.total_tokens,
        total_duration_ms=run.total_duration_ms,
        requested_by=run.requested_by,
        attempt_count=run.attempt_count,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )


@router.get("/{run_id}/events", response_model=list[RunEventResponse])
def get_run_events(
    run_id: UUID,
    limit: int = Query(default=500, ge=1, le=5000),
    _: RequestContext = Depends(require_roles(Role.viewer, Role.operator, Role.admin)),
    session: Session = Depends(get_db_session),
) -> list[RunEvent]:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    query = (
        select(RunEvent)
        .where(RunEvent.run_id == run_id)
        .order_by(RunEvent.ts.asc(), RunEvent.id.asc())
        .limit(limit)
    )
    return list(session.scalars(query).all())
