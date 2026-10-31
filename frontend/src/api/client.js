/**
 * NetCoop AI Frontend API Client.
 * Connects to FastAPI backend endpoints.
 */

const API_BASE = (import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace(/\/$/, '') : '') + '/api';

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

export async function fetchInvestigations() {
  const res = await fetch(`${API_BASE}/investigations`);
  if (!res.ok) throw new Error(`Failed to load past investigations: ${res.statusText}`);
  return res.json();
}

export async function fetchInvestigationById(incidentId) {
  const res = await fetch(`${API_BASE}/investigations/${incidentId}`);
  if (!res.ok) throw new Error(`Failed to load investigation #${incidentId}: ${res.statusText}`);
  return res.json();
}

export async function fetchDigitalTwin() {
  const res = await fetch(`${API_BASE}/digital-twin`);
  if (!res.ok) throw new Error(`Failed to load digital twin: ${res.statusText}`);
  return res.json();
}

export async function fetchRemediationStrategies(rootCause, targetDevice) {
  const params = new URLSearchParams();
  if (rootCause) params.append('root_cause', rootCause);
  if (targetDevice) params.append('target_device', targetDevice);
  const res = await fetch(`${API_BASE}/simulator/strategies?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to load remediation strategies: ${res.statusText}`);
  return res.json();
}

export async function simulateRemediation(payload) {
  const res = await fetch(`${API_BASE}/simulator/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Simulation failed with status ${res.status}`);
  }
  return res.json();
}

export async function compareRemediationStrategies(payload) {
  const res = await fetch(`${API_BASE}/simulator/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Strategy comparison failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchIncidentPrioritization() {
  const res = await fetch(`${API_BASE}/incidents/prioritization`);
  if (!res.ok) throw new Error(`Failed to load incident prioritization: ${res.statusText}`);
  return res.json();
}

export async function injectFaultAndDiagnose(payload) {
  const res = await fetch(`${API_BASE}/simulator/inject-fault`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Fault injection failed with status ${res.status}`);
  }
  return res.json();
}

// -------------------------------------------------------------
// PHASE 4: AUTONOMOUS NETWORK INTELLIGENCE CLIENT METHODS
// -------------------------------------------------------------

export async function fetchExplainableHealthBreakdown(scenarioId = null) {
  const params = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : '';
  const res = await fetch(`${API_BASE}/intelligence/health-breakdown${params}`);
  if (!res.ok) throw new Error(`Failed to load health breakdown: ${res.statusText}`);
  return res.json();
}

export async function fetchProactiveRisks(scenarioId = null) {
  const params = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : '';
  const res = await fetch(`${API_BASE}/intelligence/proactive-risks${params}`);
  if (!res.ok) throw new Error(`Failed to load proactive risk analysis: ${res.statusText}`);
  return res.json();
}

export async function fetchIncidentCorrelations(scenarioId = null) {
  const params = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : '';
  const res = await fetch(`${API_BASE}/intelligence/correlations${params}`);
  if (!res.ok) throw new Error(`Failed to load incident correlations: ${res.statusText}`);
  return res.json();
}

// -------------------------------------------------------------
// LIVE NETWORK INTEGRATIONS CLIENT METHODS
// -------------------------------------------------------------

export async function fetchNetworkSources() {
  const res = await fetch(`${API_BASE}/integrations/sources`);
  if (!res.ok) throw new Error(`Failed to load network sources: ${res.statusText}`);
  return res.json();
}

export async function createNetworkSource(data) {
  const res = await fetch(`${API_BASE}/integrations/sources`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Failed to create network source');
  }
  return res.json();
}

export async function updateNetworkSource(sourceId, data) {
  const res = await fetch(`${API_BASE}/integrations/sources/${sourceId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Failed to update network source');
  }
  return res.json();
}

export async function deleteNetworkSource(sourceId) {
  const res = await fetch(`${API_BASE}/integrations/sources/${sourceId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete source: ${res.statusText}`);
  return res.json();
}

export async function testSourceConnection(sourceId) {
  const res = await fetch(`${API_BASE}/integrations/sources/${sourceId}/test`, {
    method: 'POST',
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Connection test failed');
  }
  return res.json();
}

export async function pollSourceTelemetry(sourceId) {
  const res = await fetch(`${API_BASE}/integrations/sources/${sourceId}/poll`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to poll source: ${res.statusText}`);
  return res.json();
}

export async function diagnoseLiveNetwork(payload = {}) {
  const res = await fetch(`${API_BASE}/integrations/diagnose-live`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Live diagnosis failed');
  }
  return res.json();
}

export async function ingestSyslog(payload) {
  const res = await fetch(`${API_BASE}/integrations/syslog/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to ingest syslog messages: ${res.statusText}`);
  return res.json();
}

// -------------------------------------------------------------
// COLLECTOR AGENT & ON-PREMISE INGESTION CLIENT METHODS
// -------------------------------------------------------------

export async function fetchCollectors() {
  const res = await fetch(`${API_BASE}/collectors`);
  if (!res.ok) throw new Error(`Failed to load collectors: ${res.statusText}`);
  return res.json();
}

export async function enrollCollector(name, backendUrl = null) {
  const res = await fetch(`${API_BASE}/collectors/enroll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, backend_url: backendUrl }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Failed to enroll collector');
  }
  return res.json();
}

export async function revokeCollector(collectorId) {
  const res = await fetch(`${API_BASE}/collectors/${collectorId}/revoke`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to revoke collector: ${res.statusText}`);
  return res.json();
}

export async function fetchCollectorInventory() {
  const res = await fetch(`${API_BASE}/collectors/inventory`);
  if (!res.ok) throw new Error(`Failed to load collector inventory: ${res.statusText}`);
  return res.json();
}

export async function registerCollectorDevice(collectorId, deviceData) {
  const res = await fetch(`${API_BASE}/collectors/${collectorId}/devices`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(deviceData),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Failed to register device to collector');
  }
  return res.json();
}

export async function deleteCollectorDevice(collectorId, deviceId) {
  const res = await fetch(`${API_BASE}/collectors/${collectorId}/devices/${deviceId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to remove device: ${res.statusText}`);
  return res.json();
}
