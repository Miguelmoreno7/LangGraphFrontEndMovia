# Dokploy Deployment Notes (MVP)

Deploy each service independently so API and workers can scale separately:

1. `frontend-service`
2. `control-api-service`
3. `worker-service`
4. `redis-service`
5. `postgres` should point to Supabase (or managed Postgres) for production

## Environment Variables

Use the same env set for `control-api` and `worker` (with service-specific values where noted):

- `DATABASE_URL`
- `REDIS_URL`
- `QUEUE_NAME`
- `LOG_LEVEL`
- `APP_ENV`
- `WORKER_MAX_RETRIES` (worker only)
- `WORKER_POLL_TIMEOUT_SECONDS` (worker only)
- `OPENAI_API_KEY` (optional, depending on agent graph implementation)

## Health Checks

- Control API: `GET /health` and `GET /ready`
- Frontend: root path `/`
- Worker: process-level health from container restarts; optionally add a heartbeat sidecar if required

## Scaling

- Scale `worker-service` replicas for throughput.
- Keep `control-api-service` stateless.
- Use Redis persistence settings according to workload durability needs.

