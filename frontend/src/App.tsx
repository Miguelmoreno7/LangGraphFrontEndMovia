import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Agent,
  AgentVersion,
  Role,
  Run,
  RunEvent,
  request
} from "./api";

function prettyDate(value: string | null): string {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

function statusClass(status: Run["status"]): string {
  return `status status-${status}`;
}

const roleOptions: Role[] = ["viewer", "operator", "admin"];

function App() {
  const [role, setRole] = useState<Role>("operator");
  const [user, setUser] = useState("ops@agency.com");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [selectedVersion, setSelectedVersion] = useState<string>("");
  const [runInput, setRunInput] = useState('{\n  "lead_id": "123"\n}');
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>("");
  const [success, setSuccess] = useState<string>("");

  const enabledAgents = useMemo(
    () => agents.filter((agent) => agent.enabled),
    [agents]
  );

  async function loadAgents(): Promise<void> {
    const data = await request<Agent[]>("/agents", { role, user });
    setAgents(data);
    if (!selectedAgent && data.length > 0) {
      setSelectedAgent(data[0].id);
    }
  }

  async function loadRuns(): Promise<void> {
    const data = await request<Run[]>("/runs?limit=100", { role, user });
    setRuns(data);
  }

  async function loadVersions(agentId: string): Promise<void> {
    if (!agentId) {
      setVersions([]);
      setSelectedVersion("");
      return;
    }
    const data = await request<AgentVersion[]>(`/agents/${agentId}/versions`, {
      role,
      user
    });
    setVersions(data);
    setSelectedVersion(data[0]?.version ?? "");
  }

  async function loadEvents(runId: string): Promise<void> {
    if (!runId) {
      setEvents([]);
      return;
    }
    const data = await request<RunEvent[]>(`/runs/${runId}/events`, { role, user });
    setEvents(data);
  }

  async function refreshAll(): Promise<void> {
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await Promise.all([loadAgents(), loadRuns()]);
    } catch (requestError) {
      setError(String(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function onToggleAgent(agent: Agent, enabled: boolean): Promise<void> {
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await request<Agent>(`/agents/${agent.id}/toggle`, {
        method: "PATCH",
        role,
        user,
        body: { enabled }
      });
      setSuccess(`Agent "${agent.name}" is now ${enabled ? "enabled" : "disabled"}.`);
      await Promise.all([loadAgents(), loadRuns()]);
    } catch (requestError) {
      setError(String(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmitRun(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      const parsedInput = JSON.parse(runInput) as Record<string, unknown>;
      const response = await request<{ id: string }>("/runs", {
        method: "POST",
        role,
        user,
        body: {
          agent_id: selectedAgent,
          version: selectedVersion || undefined,
          input: parsedInput,
          requested_by: user
        }
      });
      setSelectedRun(response.id);
      setSuccess(`Run ${response.id} queued successfully.`);
      await Promise.all([loadRuns(), loadEvents(response.id)]);
    } catch (requestError) {
      setError(String(requestError));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refreshAll();
    const interval = window.setInterval(() => {
      void loadRuns();
      if (selectedRun) {
        void loadEvents(selectedRun);
      }
    }, 5000);
    return () => window.clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedAgent) {
      void loadVersions(selectedAgent);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAgent]);

  return (
    <div className="page">
      <header className="hero">
        <div>
          <h1>LangGraph Ops Platform</h1>
          <p>Toggle agents, enqueue runs, and inspect run event streams.</p>
        </div>
        <button className="button secondary" onClick={() => void refreshAll()}>
          Refresh
        </button>
      </header>

      <section className="card controls">
        <div className="field">
          <label htmlFor="role">Role</label>
          <select
            id="role"
            value={role}
            onChange={(event) => setRole(event.target.value as Role)}
          >
            {roleOptions.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="user">User</label>
          <input
            id="user"
            value={user}
            onChange={(event) => setUser(event.target.value)}
            placeholder="ops@agency.com"
          />
        </div>
        <div className="chip">
          Enabled Agents: <strong>{enabledAgents.length}</strong> / {agents.length}
        </div>
      </section>

      {error ? <section className="alert error">{error}</section> : null}
      {success ? <section className="alert success">{success}</section> : null}

      <div className="grid">
        <section className="card">
          <h2>Agents</h2>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Key</th>
                <th>Default Version</th>
                <th>Status</th>
                <th>Toggle</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td>{agent.name}</td>
                  <td>{agent.key}</td>
                  <td>{agent.default_version ?? "-"}</td>
                  <td>{agent.enabled ? "Enabled" : "Disabled"}</td>
                  <td>
                    <button
                      className="button"
                      disabled={busy || role === "viewer"}
                      onClick={() => void onToggleAgent(agent, !agent.enabled)}
                    >
                      {agent.enabled ? "Disable" : "Enable"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <h2>Run Trigger</h2>
          <form onSubmit={onSubmitRun} className="form">
            <div className="field">
              <label htmlFor="agent">Agent</label>
              <select
                id="agent"
                value={selectedAgent}
                onChange={(event) => setSelectedAgent(event.target.value)}
              >
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name} ({agent.enabled ? "on" : "off"})
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="version">Version</label>
              <select
                id="version"
                value={selectedVersion}
                onChange={(event) => setSelectedVersion(event.target.value)}
              >
                {versions.map((version) => (
                  <option key={version.id} value={version.version}>
                    {version.version} - {version.status}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="payload">JSON Payload</label>
              <textarea
                id="payload"
                value={runInput}
                onChange={(event) => setRunInput(event.target.value)}
                rows={8}
              />
            </div>
            <button
              type="submit"
              className="button accent"
              disabled={busy || role === "viewer" || !selectedAgent}
            >
              Queue Run
            </button>
          </form>
        </section>
      </div>

      <section className="card">
        <h2>Runs</h2>
        <table>
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Agent</th>
              <th>Version</th>
              <th>Status</th>
              <th>Requested By</th>
              <th>Created</th>
              <th>Started</th>
              <th>Finished</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr
                key={run.id}
                className={selectedRun === run.id ? "selected" : ""}
                onClick={() => {
                  setSelectedRun(run.id);
                  void loadEvents(run.id);
                }}
              >
                <td>{run.id.slice(0, 8)}...</td>
                <td>{run.agent_name}</td>
                <td>{run.version}</td>
                <td>
                  <span className={statusClass(run.status)}>{run.status}</span>
                </td>
                <td>{run.requested_by ?? "-"}</td>
                <td>{prettyDate(run.created_at)}</td>
                <td>{prettyDate(run.started_at)}</td>
                <td>{prettyDate(run.finished_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Run Events {selectedRun ? `(${selectedRun})` : ""}</h2>
        <div className="events">
          {events.length === 0 ? (
            <p className="empty">Select a run to view its event log.</p>
          ) : (
            events.map((eventItem) => (
              <article key={eventItem.id} className="event-line">
                <div>
                  <span className="event-ts">{prettyDate(eventItem.ts)}</span>
                  <span className={`event-level ${eventItem.level}`}>
                    {eventItem.level}
                  </span>
                  <span className="event-type">{eventItem.event_type}</span>
                </div>
                <p>{eventItem.message}</p>
                <pre>{JSON.stringify(eventItem.payload_json, null, 2)}</pre>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

export default App;

