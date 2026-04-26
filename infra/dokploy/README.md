# Dokploy Deployment Notes (MVP)

This project includes a Dokploy-oriented Compose file at:

- `dokploy.compose.yml`

The key difference vs local Docker Compose is that **no host ports are published** for internal services.  
That avoids collisions like `Bind for 0.0.0.0:6379 failed: port is already allocated`.

## Why your Redis port failed

Your previous Compose published Redis with `6379:6379`, which tries to reserve host port `6379`.
If another app in Dokploy (or host process) already uses `6379`, deployment fails.

In `dokploy.compose.yml`, Redis is internal-only (`expose: 6379`) so it does not bind host port `6379`.

## Recommended Dokploy Setup

1. Create a new Docker Compose app in Dokploy.
2. Set compose path to `dokploy.compose.yml`.
3. Add environment variables from `.env.dokploy.example` (at minimum `DATABASE_URL`).
4. Expose only `frontend` publicly (port `80` in container).
5. Keep `redis`, `control-api`, and `worker` internal unless you explicitly need external access.

## Environment Variables

Required:

- `DATABASE_URL` (Supabase or managed Postgres recommended)

Recommended:

- `REDIS_URL` (leave unset to use internal Redis service: `redis://redis:6379/0`)
- `QUEUE_NAME` (default: `runs:queue`)
- `LOG_LEVEL` (default: `INFO`)
- `APP_ENV`
- `WORKER_MAX_RETRIES` (default: `2`)
- `WORKER_POLL_TIMEOUT_SECONDS` (default: `5`)
- `CORS_ORIGINS` (set your frontend domain(s) in production)
- `OPENAI_API_KEY` (if your graphs require it)

## Health Checks

- Control API: `GET /health` and `GET /ready`
- Frontend: `/`
- Worker: rely on container restart policy, or add external checks if needed

## Scaling

- Scale `worker` replicas independently for throughput.
- Keep `control-api` stateless.
- If you switch to an external Redis, update `REDIS_URL` and remove the `redis` service.
