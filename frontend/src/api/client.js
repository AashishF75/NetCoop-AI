/**
 * NetCoop AI Frontend API Client.
 * Connects to FastAPI backend endpoints.
 */

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchTopology() {
  const res = await fetch(`${API_BASE}/topology`);
  if (!res.ok) throw new Error(`Failed to load topology: ${res.statusText}`);
  return res.json();
}

export async function fetchScenarios() {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error(`Failed to load scenarios: ${res.statusText}`);
  return res.json();
}

export async function fetchScenarioTelemetry(scenarioId) {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/telemetry`);
  if (!res.ok) throw new Error(`Failed to load telemetry for ${scenarioId}: ${res.statusText}`);
  return res.json();
}

export async function runDiagnosis({ scenarioId, telemetry, rawContent, dataFormat, incidentId }) {
  const payload = {
    scenario_id: scenarioId,
    telemetry: telemetry || null,
    raw_content: rawContent || null,
    data_format: dataFormat || 'json',
    incident_id: incidentId || null,
  };

  const res = await fetch(`${API_BASE}/diagnose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Diagnosis failed with status ${res.status}`);
  }

  return res.json();
}

export async function validateAgentMessage(messageDict) {
  const res = await fetch(`${API_BASE}/protocol/validate-message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: messageDict }),
  });
  return res.json();
}

export function getExportUrl(scenarioId, format = 'json') {
  return `${API_BASE}/scenarios/${scenarioId}/export?format=${format}`;
}
