# LangGraph Platform Bootstrap (Services-First)

This repository bootstraps an operations platform for LangGraph execution with clean service separation:

- `frontend`: operator dashboard
- `control_api`: control plane and queue producer
- `worker`: queue consumer and graph executor
- `shared`: shared contracts, settings, and persistence models
- `infra`: Docker, Dokploy notes, and SQL migrations

## Architecture

Execution flow:

1. Dashboard calls `POST /runs`.
2. Control API validates agent/version, writes `runs` and `run_events`, and enqueues a Redis job.
3. Worker consumes queue jobs, executes the selected entrypoint, writes events, and finalizes run status/output.
4. Dashboard polls `GET /runs` and `GET /runs/{id}/events`.

## Repository Layout

```text
platform/
  frontend/
  control_api/
  worker/
  shared/
    schemas/
    settings/
    db/
    queue/
  infra/
    docker/
    dokploy/
    migrations/
  docker-compose.yml
```

## API (MVP)

### Agents

- `GET /agents`
- `PATCH /agents/{agent_id}/toggle` body `{ "enabled": true|false }`
- `GET /agents/{agent_id}/versions`

### Runs

- `POST /runs`
- `GET /runs?agent_id=...&status=...`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`

### Health

- `GET /health`
- `GET /ready`

## Quick Start (Docker Compose)

1. Copy env file:

```bash
cp .env.example .env
```

2. Start stack:

```bash
docker compose up --build
```

3. Open:

- Dashboard: `http://localhost:8080`
- Control API: `http://localhost:8000`

## Seed Data

Migrations create one sample enabled agent:

- Agent key: `echo`
- Version: `v1`
- Entrypoint: `worker.agents.echo_agent:build_graph`

This agent echoes payload input to verify end-to-end platform behavior.

## Worker Contract

Redis job envelope:

```json
{
  "run_id": "uuid",
  "agent_id": "uuid",
  "version": "v1",
  "enqueued_at": "2026-04-21T00:00:00Z",
  "attempts": 0
}
```

Worker algorithm:

1. Pop job from Redis.
2. Re-check agent enabled state.
3. Resolve entrypoint `module:function`.
4. Build and execute graph.
5. Persist events and final run state.
6. Retry within `WORKER_MAX_RETRIES`.

## Notes

- API role gate is header-based for bootstrap (`X-Role`: `viewer|operator|admin`).
- `run_events` is the audit stream for queue/execution/finalization events.
- Frontend polls runs/events every 5 seconds.

