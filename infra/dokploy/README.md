# Dokploy Deployment Notes (MVP)

This project includes a Dokploy-oriented Compose file at:

- `docker-compose.yml`

The key difference vs local Docker Compose is that **no host ports are published** for internal services.  
That avoids collisions like `Bind for 0.0.0.0:6379 failed: port is already allocated`.

## Why your Redis port failed

Your previous Compose published Redis with `6379:6379`, which tries to reserve host port `6379`.
If another app in Dokploy (or host process) already uses `6379`, deployment fails.

In `docker-compose.yml`, Redis is internal-only (`expose: 6379`) so it does not bind host port `6379`.

## If You Still See `langgraph-platform-redis` Errors

That name comes from an older compose file that had fixed `container_name` values and host port binds.

1. Confirm Dokploy app points to `docker-compose.yml`.
2. Redeploy with rebuild enabled.
3. If needed, remove stale containers from the host:
   - `docker rm -f langgraph-platform-redis langgraph-platform-postgres langgraph-platform-control-api langgraph-platform-worker langgraph-platform-frontend`

## Recommended Dokploy Setup

1. Create a new Docker Compose app in Dokploy.
2. Set compose path to `docker-compose.yml`.
3. Add environment variables from `.env.dokploy.example`.
4. Expose only `frontend` publicly (port `80` in container).
5. Keep `redis`, `control-api`, and `worker` internal unless you explicitly need external access.

## Service Name vs Container Name

- Docker DNS inside a compose network resolves by **service name** (for example `control-api`), not by the generated container name.
- Dokploy may prefix container names with repository/app identifiers; this is expected and does not break service discovery.
- If `frontend` and `control-api` are deployed in different apps/networks, `control-api` will not resolve internally.
  In that case, set:
  - `CONTROL_API_BASE_URL=https://your-api-domain.com`

## Environment Variables

Required:

- None for bootstrapping (internal Postgres/Redis are included in compose)

Recommended:

- `DATABASE_URL` (set to Supabase or managed Postgres in production)
- `REDIS_URL` (leave unset to use internal Redis service: `redis://redis:6379/0`)
- `QUEUE_NAME` (default: `runs:queue`)
- `LOG_LEVEL` (default: `INFO`)
- `APP_ENV`
- `WORKER_MAX_RETRIES` (default: `2`)
- `WORKER_POLL_TIMEOUT_SECONDS` (default: `5`)
- `CORS_ORIGINS` (set your frontend domain(s) in production)
- `CONTROL_API_BASE_URL` (default: `http://control-api:8000`)
- `OPENAI_API_KEY` (if your graphs require it)

## Health Checks

- Control API: `GET /health` and `GET /ready`
- Frontend: `/`
- Worker: rely on container restart policy, or add external checks if needed

## Scaling

- Scale `worker` replicas independently for throughput.
- Keep `control-api` stateless.
- If you switch to an external Redis, update `REDIS_URL` and remove the `redis` service.
