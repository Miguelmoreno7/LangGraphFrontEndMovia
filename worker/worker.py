from __future__ import annotations

import importlib
import logging
import time
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from shared.db import Agent, AgentVersion, Run, RunEvent, SessionLocal, check_database_ready
from shared.logging_utils import configure_logging
from shared.queue import check_redis_ready, enqueue_run_job, pop_run_job
from shared.schemas import QueueJobEnvelope, RunStatus
from shared.settings import get_settings


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("worker")


def _safe_payload(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def _append_event(
    session: Session,
    run_id: UUID,
    level: str,
    event_type: str,
    message: str,
    payload: dict | None = None,
) -> None:
    session.add(
        RunEvent(
            run_id=run_id,
            level=level,
            event_type=event_type,
            message=message,
            payload_json=payload or {},
        )
    )


def _resolve_callable(entrypoint: str) -> Callable[..., Any]:
    try:
        module_name, factory_name = entrypoint.split(":", maxsplit=1)
    except ValueError as exc:
        raise RuntimeError(f"Invalid entrypoint format '{entrypoint}'. Expected module:function.") from exc

    module = importlib.import_module(module_name)
    factory = getattr(module, factory_name, None)
    if factory is None or not callable(factory):
        raise RuntimeError(f"Entrypoint '{entrypoint}' is not callable.")
    return factory


def _invoke_graph(graph: Any, payload: dict) -> Any:
    if callable(graph):
        return graph(payload)
    if hasattr(graph, "invoke") and callable(graph.invoke):
        return graph.invoke(payload)
    if hasattr(graph, "run") and callable(graph.run):
        return graph.run(payload)
    raise RuntimeError("Resolved graph object is not callable and has no invoke/run method.")


def _process_job(job: QueueJobEnvelope) -> None:
    logger.info(
        "Processing run job",
        extra={"extra": {"run_id": str(job.run_id), "agent_id": str(job.agent_id), "attempt": job.attempts}},
    )
    with SessionLocal() as session:
        run = session.get(Run, job.run_id)
        if run is None:
            logger.warning("Run does not exist anymore", extra={"extra": {"run_id": str(job.run_id)}})
            return

        agent = session.get(Agent, run.agent_id)
        version = session.get(AgentVersion, run.agent_version_id)
        if agent is None or version is None:
            run.status = RunStatus.failed.value
            run.error_text = "Agent metadata missing for execution."
            run.finished_at = datetime.now(UTC)
            _append_event(session, run.id, "error", "queue", "Missing agent metadata.", {})
            session.commit()
            return

        if not agent.enabled:
            run.status = RunStatus.cancelled.value
            run.finished_at = datetime.now(UTC)
            run.error_text = "Agent disabled before execution."
            _append_event(
                session,
                run.id,
                "warn",
                "queue",
                "Run cancelled because agent was disabled.",
                {"agent_id": str(agent.id)},
            )
            session.commit()
            return

        run.status = RunStatus.running.value
        run.started_at = run.started_at or datetime.now(UTC)
        run.attempt_count = job.attempts + 1
        _append_event(
            session,
            run.id,
            "info",
            "node_start",
            "Worker started execution.",
            {"entrypoint": version.entrypoint, "attempt": run.attempt_count},
        )
        session.commit()

        try:
            factory = _resolve_callable(version.entrypoint)
            graph = factory(version.config_json or {})
            result = _invoke_graph(graph, run.input_json or {})

            run.status = RunStatus.success.value
            run.output_json = _safe_payload(result)
            run.error_text = None
            run.finished_at = datetime.now(UTC)
            _append_event(session, run.id, "info", "final", "Run completed successfully.", _safe_payload(result))
            session.commit()
        except Exception as exc:
            run.error_text = str(exc)
            _append_event(
                session,
                run.id,
                "error",
                "node_end",
                "Execution failed.",
                {"error": str(exc), "attempt": run.attempt_count},
            )

            if job.attempts < settings.worker_max_retries:
                retry_job = QueueJobEnvelope(
                    run_id=job.run_id,
                    agent_id=job.agent_id,
                    version=job.version,
                    enqueued_at=datetime.now(UTC),
                    attempts=job.attempts + 1,
                )
                run.status = RunStatus.queued.value
                _append_event(
                    session,
                    run.id,
                    "warn",
                    "queue",
                    "Run re-queued after failure.",
                    {"next_attempt": retry_job.attempts + 1, "max_retries": settings.worker_max_retries},
                )
                session.commit()
                enqueue_run_job(retry_job)
                return

            run.status = RunStatus.failed.value
            run.finished_at = datetime.now(UTC)
            _append_event(
                session,
                run.id,
                "error",
                "final",
                "Run failed after max retries.",
                {"max_retries": settings.worker_max_retries},
            )
            session.commit()


def run_forever() -> None:
    config_issues = settings.database_config_issues()
    if config_issues:
        logger.error(
            "Supabase database configuration issues detected. Worker will not start.",
            extra={"extra": {"issues": config_issues}},
        )
        raise SystemExit(1)
    try:
        check_database_ready()
        check_redis_ready()
    except Exception as exc:
        logger.error(
            "Worker startup dependency checks failed. Worker will not start.",
            extra={"extra": {"error": str(exc)}},
        )
        raise SystemExit(1)

    logger.info(
        "Worker loop started",
        extra={"extra": {"queue_name": settings.queue_name, "poll_timeout": settings.worker_poll_timeout_seconds}},
    )
    while True:
        try:
            job = pop_run_job(timeout_seconds=settings.worker_poll_timeout_seconds)
            if job is None:
                continue
            _process_job(job)
        except KeyboardInterrupt:
            logger.info("Worker interrupted; stopping.")
            break
        except Exception as exc:
            logger.exception("Worker loop error: %s", exc)
            time.sleep(2)


if __name__ == "__main__":
    run_forever()
