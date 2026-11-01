/**
 * NetCoop AI Frontend API Client.
 * Connects to FastAPI backend endpoints.
 */

const PROD_RENDER_URL = 'https://netcoop-ai-backend.onrender.com';

function resolveApiBase() {
  const envUrl = (import.meta.env.VITE_API_URL || '').trim();
  if (envUrl) {
    return envUrl.replace(/\/$/, '') + '/api';
  }
  // When running on Vercel deployment, default to production Render backend URL
  if (typeof window !== 'undefined' && window.location.hostname.includes('vercel.app')) {
    return `${PROD_RENDER_URL}/api`;
  }
  // Fallback for local Vite dev proxy or relative path
  return '/api';
}

export const API_BASE = resolveApiBase();

/**
 * Resolves the actual FastAPI backend base URL for standalone tools like the collector CLI.
 * Ensures the collector connects to the FastAPI backend (port 8000), never the Vite frontend (port 5173).
 */
export function getBackendBaseUrl() {
  const envUrl = (import.meta.env.VITE_API_URL || '').trim();
  if (envUrl) {
    return envUrl.replace(/\/api\/?$/, '').replace(/\/$/, '');
  }
  // When running on Vercel deployment, default to production Render backend URL
  if (typeof window !== 'undefined' && window.location.hostname.includes('vercel.app')) {
    return PROD_RENDER_URL;
  }
  // When running on local dev server (Vite on :5173), point to FastAPI backend on port 8000
  if (typeof window !== 'undefined') {
    const { hostname, port, protocol } = window.location;
    if (port === '5173' || hostname === 'localhost' || hostname === '127.0.0.1') {
      return `${protocol}//${hostname}:8000`;
    }
    return window.location.origin;
  }
  return 'http://127.0.0.1:8000';
}

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

export async function validateTarget(target) {
  const res = await fetch(`${API_BASE}/integrations/validate-target?target=${encodeURIComponent(target)}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Target validation failed');
  }
  return res.json();
}

export async function probeDeviceIp(payload) {
  const res = await fetch(`${API_BASE}/integrations/probe-ip`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    const err = new Error(errorData.detail || 'IP probe failed');
    err.error_code = errorData.error_code;
    err.detail = errorData.detail;
    err.is_private_target = errorData.is_private_target;
    err.can_retry = errorData.can_retry;
    throw err;
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

export async function generateOfficialTelemetry(faultType = 'normal') {
  const res = await fetch(`${API_BASE}/generator/generate?fault_type=${encodeURIComponent(faultType)}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Failed to generate official telemetry');
  }
  return res.json();
}

export async function validateOfficialTelemetry(payload) {
  const res = await fetch(`${API_BASE}/generator/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Official telemetry validation failed');
  }
  return res.json();
}

export async function diagnoseOfficialTelemetry({ faultType, rawTelemetry }) {
  const res = await fetch(`${API_BASE}/generator/diagnose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      fault_type: faultType || 'normal',
      raw_telemetry: rawTelemetry || null,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Diagnosis on generated telemetry failed');
  }
  return res.json();
}
