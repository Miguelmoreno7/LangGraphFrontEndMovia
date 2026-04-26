from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import RequestContext, require_roles
from shared.db import Agent, AgentVersion, get_db_session
from shared.schemas import AgentResponse, AgentToggleRequest, AgentVersionResponse, Role


router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
def list_agents(
    _: RequestContext = Depends(require_roles(Role.viewer, Role.operator, Role.admin)),
    session: Session = Depends(get_db_session),
) -> list[Agent]:
    query = select(Agent).order_by(Agent.created_at.desc())
    return list(session.scalars(query).all())


@router.patch("/{agent_id}/toggle", response_model=AgentResponse)
def toggle_agent(
    agent_id: UUID,
    payload: AgentToggleRequest,
    _: RequestContext = Depends(require_roles(Role.operator, Role.admin)),
    session: Session = Depends(get_db_session),
) -> Agent:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    agent.enabled = payload.enabled
    agent.updated_at = datetime.now(UTC)
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.get("/{agent_id}/versions", response_model=list[AgentVersionResponse])
def list_agent_versions(
    agent_id: UUID,
    _: RequestContext = Depends(require_roles(Role.viewer, Role.operator, Role.admin)),
    session: Session = Depends(get_db_session),
) -> list[AgentVersion]:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    query = (
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.created_at.desc())
    )
    return list(session.scalars(query).all())

