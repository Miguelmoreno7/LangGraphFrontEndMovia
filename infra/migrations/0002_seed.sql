WITH upsert_agent AS (
  INSERT INTO agents (key, name, enabled, default_version)
  VALUES ('echo', 'Echo Agent', TRUE, 'v1')
  ON CONFLICT (key)
  DO UPDATE SET
    name = EXCLUDED.name,
    enabled = EXCLUDED.enabled,
    default_version = EXCLUDED.default_version,
    updated_at = NOW()
  RETURNING id
)
INSERT INTO agent_versions (
  agent_id,
  version,
  entrypoint,
  config_json,
  status
)
SELECT
  ua.id,
  'v1',
  'worker.agents.echo_agent:build_graph',
  '{"mode":"echo"}'::jsonb,
  'active'
FROM upsert_agent ua
ON CONFLICT (agent_id, version)
DO UPDATE SET
  entrypoint = EXCLUDED.entrypoint,
  config_json = EXCLUDED.config_json,
  status = EXCLUDED.status;

