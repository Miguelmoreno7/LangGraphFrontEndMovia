# Dokploy Deployment Notes (MVP)

This project includes a Dokploy-oriented Compose file at:

- `docker-compose.yml`

The key difference vs local Docker Compose is that **no host ports are published** for internal services.  
That avoids collisions like `Bind for 0.0.0.0:6379 failed: port is already allocated`.

## Why your Redis port failed

Your previous Compose published Redis with `6379:6379`, which tries to reserve host port `6379`.
If another app in Dokploy (or host process) already uses `6379`, deployment fails.

In `docker-compose.yml`, Redis is internal-only (`expose: 6379`) so it does not bind host port `6379`.

## Recommended Dokploy Setup

1. Create a new Docker Compose app in Dokploy.
2. Set compose path to `docker-compose.yml`.
3. Add environment variables from `.env.dokploy.example`.
4. Expose only `frontend` publicly (port `80` in container).
5. Keep `redis`, `control-api`, and `worker` internal unless you explicitly need external access.

## Service Names in This Compose

This compose pins stable container names for Dokploy single-app deployments:

- `frontend`
- `control-api`
- `worker`
- `redis`

Frontend proxies `/api/*` to `control-api:8000` on the same internal network.

## Environment Variables

Required:

- `DATABASE_URL` (Supabase Postgres URI with `sslmode=require`)
- `REQUIRE_SUPABASE_DATABASE=true`

Recommended:

- `REDIS_URL` (leave unset to use internal Redis service: `redis://redis:6379/0`)
- `QUEUE_NAME` (default: `runs:queue`)
- `LOG_LEVEL` (default: `INFO`)
- `APP_ENV`
- `WORKER_MAX_RETRIES` (default: `2`)
- `WORKER_POLL_TIMEOUT_SECONDS` (default: `5`)
- `AGENT_WEBHOOK_BASE_URL` (required for distributed client-agent webhook fallback when platform worker cannot import local modules)
- `AGENT_WEBHOOK_TIMEOUT_SECONDS` (default: `30`)
- `AGENT_WEBHOOK_DISPATCHER_TOKEN` (optional, forwarded as `X-Dispatcher-Token`)
- `CORS_ORIGINS` (set your frontend domain(s) in production)
- `OPENAI_API_KEY` (if your graphs require it)

## Health Checks

- Control API: `GET /health` and `GET /ready`
- Frontend: `/`
- Worker: rely on container restart policy, or add external checks if needed

If Supabase auth/connection is wrong, `GET /ready` returns `503` with detailed configuration issues and services log those issues on startup.

## Scaling

- Scale `worker` replicas independently for throughput.
- Keep `control-api` stateless.
- If you switch to an external Redis, update `REDIS_URL` and remove the `redis` service.
