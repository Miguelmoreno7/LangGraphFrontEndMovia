export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "/api";

export type Role = "viewer" | "operator" | "admin";

export type Agent = {
  id: string;
  key: string;
  name: string;
  enabled: boolean;
  default_version: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentVersion = {
  id: string;
  agent_id: string;
  version: string;
  entrypoint: string;
  config_json: Record<string, unknown>;
  status: string;
  created_at: string;
};

export type Run = {
  id: string;
  status: "queued" | "running" | "success" | "failed" | "cancelled";
  agent_id: string;
  agent_key: string;
  agent_name: string;
  version: string;
  requested_by: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_text: string | null;
};

export type RunEvent = {
  id: number;
  run_id: string;
  ts: string;
  level: string;
  event_type: string;
  message: string;
  payload_json: Record<string, unknown>;
};

type RequestOptions = {
  method?: "GET" | "POST" | "PATCH";
  role: Role;
  user: string;
  body?: unknown;
};

export async function request<T>(
  path: string,
  { method = "GET", role, user, body }: RequestOptions
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-Role": role,
      "X-User": user
    },
    body: body ? JSON.stringify(body) : undefined
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}
