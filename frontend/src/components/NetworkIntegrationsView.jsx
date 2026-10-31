import React, { useState, useEffect } from 'react';
import {
  fetchNetworkSources,
  createNetworkSource,
  updateNetworkSource,
  deleteNetworkSource,
  testSourceConnection,
  pollSourceTelemetry,
  diagnoseLiveNetwork,
  ingestSyslog,
  fetchCollectors,
  enrollCollector,
  revokeCollector,
  fetchCollectorInventory,
  registerCollectorDevice,
  deleteCollectorDevice,
} from '../api/client';

export default function NetworkIntegrationsView({ onSelectLiveInvestigation, currentTelemetryOrigin }) {
  // Navigation sub-view: 'collectors' | 'direct_probes'
  const [subView, setSubView] = useState('collectors');

  // Direct Sources State
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFilter, setSelectedFilter] = useState('ALL');
  const [testingSourceId, setTestingSourceId] = useState(null);
  const [pollingSourceId, setPollingSourceId] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [polledTelemetryData, setPolledTelemetryData] = useState(null);

  // Collector Hub State
  const [collectors, setCollectors] = useState([]);
  const [devices, setDevices] = useState([]);
  const [enrollmentData, setEnrollmentData] = useState(null);
  const [showEnrollModal, setShowEnrollModal] = useState(false);
  const [showDeviceModal, setShowDeviceModal] = useState(false);
  const [selectedCollectorId, setSelectedCollectorId] = useState(null);
  const [enrollingCollector, setEnrollingCollector] = useState(false);
  const [collectorNameInput, setCollectorNameInput] = useState('');
  const [copySuccessMsg, setCopySuccessMsg] = useState(null);

  // Live Diagnosis State
  const [diagnosingLive, setDiagnosingLive] = useState(false);
  const [liveDiagnosisResult, setLiveDiagnosisResult] = useState(null);

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showSyslogModal, setShowSyslogModal] = useState(false);

  // Device Form State
  const [newDevice, setNewDevice] = useState({
    device_id: '',
    name: '',
    device_type: 'router',
    ip: '192.168.1.1',
    port: 80,
    protocol: 'TCP_PROBE',
  });
  const [deviceFormError, setDeviceFormError] = useState(null);

  // Direct Source form state
  const [newSource, setNewSource] = useState({
    name: '',
    source_type: 'PING_PROBE',
    host: '127.0.0.1',
    port: 80,
    endpoint_path: '',
    auth_type: 'NONE',
    community_string: '',
    username: '',
    password: '',
    api_key: '',
    bearer_token: '',
    polling_interval_sec: 30,
    timeout_sec: 2.0,
  });
  const [formError, setFormError] = useState(null);

  // Syslog form state
  const [syslogText, setSyslogText] = useState('');
  const [syslogFeedback, setSyslogFeedback] = useState(null);

  useEffect(() => {
    loadAll();
    const timer = setInterval(() => {
      loadCollectorInventory();
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  async function loadAll() {
    setLoading(true);
    await Promise.all([loadSources(), loadCollectorInventory()]);
    setLoading(false);
  }

  async function loadSources() {
    try {
      const data = await fetchNetworkSources();
      setSources(data);
    } catch (err) {
      setError(err.message || 'Failed to load network sources');
    }
  }

  async function loadCollectorInventory() {
    try {
      const data = await fetchCollectorInventory();
      setCollectors(data.collectors || []);
      setDevices(data.devices || []);
    } catch (err) {
      console.warn('Failed to load collector inventory:', err);
    }
  }

  async function handleEnrollCollector(e) {
    e.preventDefault();
    setEnrollingCollector(true);
    try {
      const backendUrl = window.location.origin;
      const res = await enrollCollector(collectorNameInput || 'LAN-Collector-01', backendUrl);
      setEnrollmentData(res);
      setCollectorNameInput('');
      await loadCollectorInventory();
    } catch (err) {
      alert(`Enrollment failed: ${err.message}`);
    } finally {
      setEnrollingCollector(false);
    }
  }

  async function handleRevokeCollector(collectorId) {
    if (!window.confirm(`Revoke collector '${collectorId}'? Outbound telemetry from this collector will be rejected.`)) {
      return;
    }
    try {
      await revokeCollector(collectorId);
      await loadCollectorInventory();
    } catch (err) {
      alert(`Revocation failed: ${err.message}`);
    }
  }

  async function handleRegisterDevice(e) {
    e.preventDefault();
    setDeviceFormError(null);
    if (!selectedCollectorId) {
      setDeviceFormError('Please select a collector.');
      return;
    }
    try {
      await registerCollectorDevice(selectedCollectorId, {
        ...newDevice,
        port: parseInt(newDevice.port, 10) || 80,
      });
      setShowDeviceModal(false);
      setNewDevice({
        device_id: '',
        name: '',
        device_type: 'router',
        ip: '192.168.1.1',
        port: 80,
        protocol: 'TCP_PROBE',
      });
      await loadCollectorInventory();
    } catch (err) {
      setDeviceFormError(err.message);
    }
  }

  async function handleDeleteDevice(collectorId, deviceId) {
    if (!window.confirm(`Remove device '${deviceId}' from collector?`)) return;
    try {
      await deleteCollectorDevice(collectorId, deviceId);
      await loadCollectorInventory();
    } catch (err) {
      alert(`Failed to delete device: ${err.message}`);
    }
  }

  function copyToClipboard(text, label = 'Command') {
    navigator.clipboard.writeText(text);
    setCopySuccessMsg(`${label} copied to clipboard!`);
    setTimeout(() => setCopySuccessMsg(null), 3000);
  }

  async function handleTestSource(sourceId) {
    setTestingSourceId(sourceId);
    try {
      const res = await testSourceConnection(sourceId);
      setTestResults((prev) => ({ ...prev, [sourceId]: res }));
      const updated = await fetchNetworkSources();
      setSources(updated);
    } catch (err) {
      alert(`Test probe error: ${err.message}`);
    } finally {
      setTestingSourceId(null);
    }
  }

  async function handlePollSource(sourceId) {
    setPollingSourceId(sourceId);
    try {
      const res = await pollSourceTelemetry(sourceId);
      setPolledTelemetryData({ sourceId, ...res });
      const updated = await fetchNetworkSources();
      setSources(updated);
    } catch (err) {
      alert(`Polling error: ${err.message}`);
    } finally {
      setPollingSourceId(null);
    }
  }

  async function handleToggleSource(source) {
    try {
      await updateNetworkSource(source.id, { enabled: !source.enabled });
      await loadSources();
    } catch (err) {
      alert(`Update failed: ${err.message}`);
    }
  }

  async function handleDeleteSource(sourceId) {
    if (!window.confirm(`Are you sure you want to remove network source '${sourceId}'?`)) return;
    try {
      await deleteNetworkSource(sourceId);
      await loadSources();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  }

  async function handleCreateSource(e) {
    e.preventDefault();
    setFormError(null);
    try {
      await createNetworkSource({
        ...newSource,
        port: parseInt(newSource.port, 10) || 80,
        polling_interval_sec: parseInt(newSource.polling_interval_sec, 10) || 30,
        timeout_sec: parseFloat(newSource.timeout_sec) || 2.0,
      });
      setShowAddModal(false);
      setNewSource({
        name: '',
        source_type: 'PING_PROBE',
        host: '127.0.0.1',
        port: 80,
        endpoint_path: '',
        auth_type: 'NONE',
        community_string: '',
        username: '',
        password: '',
        api_key: '',
        bearer_token: '',
        polling_interval_sec: 30,
        timeout_sec: 2.0,
      });
      await loadSources();
    } catch (err) {
      setFormError(err.message);
    }
  }

  async function handleRunLiveDiagnosis() {
    setDiagnosingLive(true);
    setLiveDiagnosisResult(null);
    try {
      const res = await diagnoseLiveNetwork();
      setLiveDiagnosisResult(res);
      await loadCollectorInventory();
      await loadSources();
    } catch (err) {
      alert(`Live diagnosis error: ${err.message}`);
    } finally {
      setDiagnosingLive(false);
    }
  }

  async function handleIngestSyslog() {
    if (!syslogText.trim()) return;
    try {
      const lines = syslogText.split('\n').filter((l) => l.trim().length > 0);
      const res = await ingestSyslog({ messages: lines });
      setSyslogFeedback(`Successfully ingested ${res.ingested_messages} syslog message(s).`);
      setSyslogText('');
      setTimeout(() => setSyslogFeedback(null), 4000);
      await loadSources();
    } catch (err) {
      alert(`Syslog ingestion failed: ${err.message}`);
    }
  }

  function applySyslogPreset(preset) {
    if (preset === 'link_down') {
      setSyslogText(
        '%LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down\n' +
        '%LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/1, changed state to down'
      );
    } else if (preset === 'duplex_crc') {
      setSyslogText(
        'Duplex mismatch detected on FastEthernet0/1 (half duplex), partner is full duplex.\n' +
        '%ETH-4-CRC: Interface GigabitEthernet0/1 excessive frame FCS/CRC discards (820 errors)'
      );
    } else if (preset === 'cpu_saturation') {
      setSyslogText(
        '%SYS-1-CPURISINGTHRESHOLD: High CPU utilization detected: 98% in last 5 minutes on Core-Router-01'
      );
    }
  }

  const onlineCollectors = collectors.filter((c) => c.status === 'ONLINE');
  const connectedCount = sources.filter((s) => s.status === 'CONNECTED').length;
  const streamingDevices = devices.filter((d) => d.status === 'STREAMING_LIVE');

  const filteredSources = sources.filter((s) => {
    if (selectedFilter === 'ALL') return true;
    return s.source_type === selectedFilter;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner & Title */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-2xl">🔌</span>
              <h2 className="text-xl font-bold text-white tracking-wide">
                Live Network Integrations & Telemetry Adapters
              </h2>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                  onlineCollectors.length > 0 || streamingDevices.length > 0
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                }`}
              >
                {onlineCollectors.length > 0
                  ? `🟢 ${onlineCollectors.length} Collector(s) Online (${streamingDevices.length} Streaming)`
                  : '🟣 Simulation / Local Probe Mode'}
              </span>
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Deployable on-premise network collectors stream private LAN router/switch telemetry securely outbound via HTTPS to the cloud NOC.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setShowEnrollModal(true)}
              className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition flex items-center gap-1.5 shadow-md"
            >
              <span>🔑</span> Pair New Collector
            </button>
            <button
              onClick={() => {
                if (collectors.length === 0) {
                  alert('Please pair a collector first before registering devices.');
                  return;
                }
                setSelectedCollectorId(collectors[0].collector_id);
                setShowDeviceModal(true);
              }}
              className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-sm font-medium transition flex items-center gap-1.5"
            >
              <span>➕</span> Register LAN Device
            </button>
            <button
              onClick={handleRunLiveDiagnosis}
              disabled={diagnosingLive}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition flex items-center gap-2 shadow-lg ${
                diagnosingLive
                  ? 'bg-emerald-700 text-white cursor-wait opacity-80'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/30'
              }`}
            >
              {diagnosingLive ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>Diagnosing Live Telemetry...</span>
                </>
              ) : (
                <>
                  <span>⚡</span>
                  <span>Run Live Diagnosis</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Global Summary Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-5 border-t border-slate-800">
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
            <div className="text-xs text-slate-400 font-medium">On-Premise Collectors</div>
            <div className="text-xl font-bold text-slate-100 mt-1">
              {onlineCollectors.length} <span className="text-xs text-slate-400 font-normal">/ {collectors.length} paired</span>
            </div>
          </div>
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
            <div className="text-xs text-slate-400 font-medium">Monitored LAN Devices</div>
            <div className="text-xl font-bold text-indigo-300 mt-1">
              {streamingDevices.length} <span className="text-xs text-slate-400 font-normal">/ {devices.length} registered</span>
            </div>
          </div>
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
            <div className="text-xs text-slate-400 font-medium">Direct Host Reachability</div>
            <div className="text-xl font-bold text-emerald-400 mt-1">{connectedCount} Active</div>
          </div>
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
            <div className="text-xs text-slate-400 font-medium">Transport Security</div>
            <div className="text-xl font-bold text-cyan-300 mt-1">Outbound HTTPS / WSS</div>
          </div>
        </div>
      </div>

      {/* Copy notification toast */}
      {copySuccessMsg && (
        <div className="bg-emerald-900/80 border border-emerald-500 text-emerald-100 px-4 py-2 rounded-lg text-xs font-mono flex items-center justify-between shadow-lg">
          <span>{copySuccessMsg}</span>
          <button onClick={() => setCopySuccessMsg(null)} className="underline text-[11px]">Dismiss</button>
        </div>
      )}

      {/* Live Diagnosis Result Notification Banner */}
      {liveDiagnosisResult && (
        <div className="bg-emerald-950/40 border border-emerald-500/50 rounded-xl p-5 shadow-2xl space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-emerald-400 animate-pulse"></span>
              <h3 className="text-base font-bold text-emerald-200">
                Live Multi-Agent Diagnosis Complete ({liveDiagnosisResult.incident_id})
              </h3>
              <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 text-xs font-bold rounded">
                {liveDiagnosisResult.telemetry_origin === 'LIVE_DEVICE' ? '🟢 LIVE_DEVICE TELEMETRY' : '🟢 LIVE_HOST TELEMETRY'}
              </span>
            </div>
            {onSelectLiveInvestigation && (
              <button
                onClick={() => onSelectLiveInvestigation(liveDiagnosisResult.incident_id)}
                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-bold transition flex items-center gap-1.5 shadow"
              >
                <span>🔍</span> Open in Investigation Replay
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-slate-950/70 p-3.5 rounded-lg border border-slate-800 text-sm">
            <div>
              <span className="text-slate-400 text-xs block">Suspected Root Cause</span>
              <span className="font-bold text-slate-100">{liveDiagnosisResult.report?.suspected_root_cause || 'Nominal Network Operation'}</span>
            </div>
            <div>
              <span className="text-slate-400 text-xs block">Agent Consensus Confidence</span>
              <span className="font-bold text-emerald-400">
                {liveDiagnosisResult.report ? `${Math.round(liveDiagnosisResult.report.confidence * 100)}%` : '98%'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 text-xs block">Live Sources Polled</span>
              <span className="font-bold text-indigo-300">
                {(liveDiagnosisResult.devices_polled || liveDiagnosisResult.sources_polled || ['Local Host Probe']).join(', ')} ({liveDiagnosisResult.records_collected} records)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Sub-View Navigation Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setSubView('collectors')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition ${
            subView === 'collectors'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <span>📡</span>
          <span>On-Premise Network Collectors & Device Inventory ({collectors.length})</span>
        </button>

        <button
          onClick={() => setSubView('direct_probes')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition ${
            subView === 'direct_probes'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
          }`}
        >
          <span>🖥️</span>
          <span>Direct Host Probes & Templates ({sources.length})</span>
        </button>
      </div>

      {/* ============================================================== */}
      {/* SUB-VIEW 1: ON-PREMISE COLLECTORS & REAL DEVICE INVENTORY       */}
      {/* ============================================================== */}
      {subView === 'collectors' && (
        <div className="space-y-6">
          {/* Architecture Explanation Box */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 text-xs text-slate-300 space-y-2">
            <div className="font-semibold text-slate-100 flex items-center gap-2">
              <span className="text-cyan-400">🛡️ Deployable Network Topology Architecture</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">Outbound Only</span>
            </div>
            <p className="text-slate-400">
              The <strong>Local Network Collector Agent</strong> runs on any computer (Windows / Linux) inside your LAN. It polls your actual routers, switches, and APs locally via SNMP, RESTCONF, and active TCP probes, then streams telemetry outbound over HTTPS to this backend. <em>No router management ports are ever exposed to the public internet.</em>
            </p>
          </div>

          {/* Collectors List */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>📡</span> Paired Collector Agents
              </h3>
              <button
                onClick={() => setShowEnrollModal(true)}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
              >
                + Pair Another Collector
              </button>
            </div>

            {collectors.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-3">
                <div className="text-3xl">📡</div>
                <div className="text-sm font-bold text-slate-200">No On-Premise Collectors Paired Yet</div>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  To monitor physical hardware on your local network (e.g. 192.168.1.1 or 10.0.0.1), pair a local collector agent on a laptop or server inside the network.
                </p>
                <button
                  onClick={() => setShowEnrollModal(true)}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold"
                >
                  Generate Pairing Token & Command
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {collectors.map((c) => (
                  <div
                    key={c.collector_id}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 shadow-md"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100 text-sm">{c.name}</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
                            {c.collector_id}
                          </span>
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          {c.hostname || 'Host'} ({c.local_ip || 'LAN IP'}) • {c.os_type || 'OS'}
                        </div>
                      </div>

                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                          c.status === 'ONLINE'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                            : c.status === 'REVOKED'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}
                      >
                        {c.status === 'ONLINE' && '🟢 '}
                        {c.status === 'REVOKED' && '🔴 '}
                        {c.status === 'OFFLINE' && '⚪ '}
                        {c.status}
                      </span>
                    </div>

                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 text-xs flex items-center justify-between text-slate-400">
                      <span>Monitored Devices: <strong className="text-slate-200">{c.registered_devices?.length || 0}</strong></span>
                      <span>Last Heartbeat: <strong className="text-slate-200">{c.last_heartbeat_at ? new Date(c.last_heartbeat_at).toLocaleTimeString() : 'Never'}</strong></span>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                      <button
                        onClick={() => {
                          setSelectedCollectorId(c.collector_id);
                          setShowDeviceModal(true);
                        }}
                        className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold"
                      >
                        + Add LAN Device
                      </button>

                      {c.status !== 'REVOKED' && (
                        <button
                          onClick={() => handleRevokeCollector(c.collector_id)}
                          className="px-2.5 py-1 text-rose-400 hover:bg-rose-950/40 rounded text-xs transition"
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Registered Devices Inventory */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>🖥️</span> Monitored LAN Devices Inventory ({devices.length})
              </h3>
              {collectors.length > 0 && (
                <button
                  onClick={() => {
                    setSelectedCollectorId(collectors[0].collector_id);
                    setShowDeviceModal(true);
                  }}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                >
                  + Add Local Device
                </button>
              )}
            </div>

            {devices.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center text-slate-400 text-xs">
                No physical devices registered on collectors yet. Click "+ Add Local Device" to register a router, switch, or AP.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {devices.map((d) => (
                  <div
                    key={d.device_id}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3 shadow-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100 text-sm">{d.name}</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {d.device_type}
                          </span>
                        </div>
                        <div className="text-xs font-mono text-slate-400 mt-1">
                          {d.ip}:{d.port} • [{d.protocol}] • Collector: {d.collector_id}
                        </div>
                      </div>

                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                          d.status === 'STREAMING_LIVE'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                            : d.status === 'STALE_TELEMETRY'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : d.status === 'AUTH_REJECTED'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}
                      >
                        {d.status === 'STREAMING_LIVE' && '🟢 '}
                        {d.status === 'STALE_TELEMETRY' && '🟡 '}
                        {d.status === 'AUTH_REJECTED' && '🔒 '}
                        {d.status}
                      </span>
                    </div>

                    {/* Metric Availability Chips */}
                    <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
                      <div className="text-[11px] text-slate-400">Available Metrics:</div>
                      <div className="flex flex-wrap gap-1">
                        {d.metrics_available && d.metrics_available.length > 0 ? (
                          d.metrics_available.map((m) => (
                            <span
                              key={m}
                              className="text-[10px] px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/60"
                            >
                              ✓ {m}
                            </span>
                          ))
                        ) : (
                          <span className="text-[10px] text-slate-500">Awaiting first polling cycle</span>
                        )}
                      </div>

                      {d.metrics_unsupported && d.metrics_unsupported.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {d.metrics_unsupported.map((m) => (
                            <span
                              key={m}
                              className="text-[10px] px-2 py-0.5 rounded bg-slate-950 text-slate-500 border border-slate-800"
                            >
                              ✕ {m} (not exposed by device)
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs text-slate-400">
                      <span>Latest Telemetry: <strong className="text-slate-200">{d.last_telemetry_at ? new Date(d.last_telemetry_at).toLocaleTimeString() : 'Pending'}</strong></span>
                      <button
                        onClick={() => handleDeleteDevice(d.collector_id, d.device_id)}
                        className="text-slate-500 hover:text-rose-400 transition"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* SUB-VIEW 2: DIRECT HOST ADAPTERS & MIB TEMPLATES               */}
      {/* ============================================================== */}
      {subView === 'direct_probes' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>🖥️</span> Direct Host Probes & Templates
            </h3>
            <button
              onClick={() => setShowAddModal(true)}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
            >
              + Add Direct Source
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredSources.map((source) => {
              const isTesting = testingSourceId === source.id;
              const isPolling = pollingSourceId === source.id;
              const testResult = testResults[source.id];

              return (
                <div
                  key={source.id}
                  className={`bg-slate-900 border rounded-xl p-5 shadow-lg flex flex-col justify-between transition-all ${
                    source.enabled
                      ? source.status === 'CONNECTED'
                        ? 'border-emerald-600/40 hover:border-emerald-500/60'
                        : source.status === 'DEGRADED'
                        ? 'border-amber-600/40 hover:border-amber-500/60'
                        : 'border-slate-800 hover:border-slate-700'
                      : 'border-slate-800/60 opacity-60'
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100 text-base">{source.name}</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                            {source.source_type}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-400 mt-1 font-mono">
                          <span>{source.host}:{source.port}{source.endpoint_path || ''}</span>
                        </div>
                      </div>

                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-bold tracking-wide uppercase ${
                          source.status === 'CONNECTED'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                            : source.status === 'DEGRADED'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : source.status === 'DISCONNECTED'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}
                      >
                        {source.status === 'CONNECTED' && '🟢 '}
                        {source.status === 'DEGRADED' && '🟡 '}
                        {source.status === 'DISCONNECTED' && '🔴 '}
                        {source.status === 'UNKNOWN' && '⚪ '}
                        {source.status}
                      </span>
                    </div>

                    <div className="mt-4 p-3 bg-slate-950 rounded-lg border border-slate-800/80 text-xs space-y-1.5">
                      {testResult ? (
                        <div>
                          <div className="text-slate-300 font-medium">{testResult.message}</div>
                          {testResult.latency_ms !== null && (
                            <div className="flex items-center gap-4 text-slate-400 mt-1">
                              <span>RTT: <strong className="text-emerald-400">{testResult.latency_ms} ms</strong></span>
                              {testResult.jitter_ms !== null && <span>Jitter: <strong className="text-indigo-400">{testResult.jitter_ms} ms</strong></span>}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-slate-400">Click Test Connection to probe socket reachability.</div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-2 mt-4 pt-4 border-t border-slate-800/60">
                    <button
                      onClick={() => handleTestSource(source.id)}
                      disabled={isTesting}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold transition border border-slate-700"
                    >
                      {isTesting ? 'Testing...' : '🔌 Test Connection'}
                    </button>
                    <button
                      onClick={() => handleToggleSource(source)}
                      className="px-2.5 py-1 text-xs font-medium rounded bg-slate-800 text-slate-300"
                    >
                      {source.enabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* MODAL: PAIR NEW COLLECTOR & SETUP INSTRUCTIONS                 */}
      {/* ============================================================== */}
      {showEnrollModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>🔑</span> Pair New On-Premise Network Collector
              </h3>
              <button onClick={() => setShowEnrollModal(false)} className="text-slate-400 hover:text-white text-lg font-bold">✕</button>
            </div>

            {!enrollmentData ? (
              <form onSubmit={handleEnrollCollector} className="space-y-4 mt-4 text-xs">
                <p className="text-slate-400">
                  Generate a cryptographic enrollment token to pair an on-premise collector running on your private network.
                </p>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Collector Identifier / Site Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Campus-Lab-Collector"
                    value={collectorNameInput}
                    onChange={(e) => setCollectorNameInput(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-slate-100"
                  />
                </div>

                <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setShowEnrollModal(false)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={enrollingCollector}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-bold"
                  >
                    {enrollingCollector ? 'Generating Token...' : 'Generate Pairing Token'}
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-4 mt-4 text-xs">
                <div className="p-3 bg-emerald-950/40 border border-emerald-600/40 rounded-lg text-emerald-200">
                  <strong>Collector Enrolled:</strong> {enrollmentData.collector_id} ({enrollmentData.name})
                </div>

                <div className="space-y-2">
                  <label className="block text-slate-300 font-semibold">1. Windows Pairing Command (PowerShell / CMD)</label>
                  <div className="flex items-center gap-2">
                    <pre className="flex-1 bg-slate-950 p-2.5 rounded font-mono text-[11px] text-cyan-300 border border-slate-800 overflow-x-auto">
                      {enrollmentData.pairing_command_windows}
                    </pre>
                    <button
                      onClick={() => copyToClipboard(enrollmentData.pairing_command_windows, 'Windows command')}
                      className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-semibold text-xs whitespace-nowrap"
                    >
                      Copy
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block text-slate-300 font-semibold">2. Linux Pairing Command (Bash)</label>
                  <div className="flex items-center gap-2">
                    <pre className="flex-1 bg-slate-950 p-2.5 rounded font-mono text-[11px] text-cyan-300 border border-slate-800 overflow-x-auto">
                      {enrollmentData.pairing_command_linux}
                    </pre>
                    <button
                      onClick={() => copyToClipboard(enrollmentData.pairing_command_linux, 'Linux command')}
                      className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-semibold text-xs whitespace-nowrap"
                    >
                      Copy
                    </button>
                  </div>
                </div>

                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-400 space-y-1">
                  <strong className="text-slate-200 block">How It Works:</strong>
                  <div>• Collector runs locally on your computer inside the network.</div>
                  <div>• Initiates outbound connection to NetCoop AI backend.</div>
                  <div>• Router credentials stay strictly on your local machine.</div>
                  <div>• Token expires in 24 hours: <span className="font-mono text-slate-300">{enrollmentData.expires_at}</span></div>
                </div>

                <div className="pt-3 flex justify-end">
                  <button
                    onClick={() => {
                      setEnrollmentData(null);
                      setShowEnrollModal(false);
                    }}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-bold"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* MODAL: REGISTER LOCAL DEVICE ON COLLECTOR                      */}
      {/* ============================================================== */}
      {showDeviceModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>➕</span> Register LAN Device on Collector
              </h3>
              <button onClick={() => setShowDeviceModal(false)} className="text-slate-400 hover:text-white text-lg font-bold">✕</button>
            </div>

            {deviceFormError && (
              <div className="mt-3 p-2.5 bg-rose-950/50 border border-rose-800 text-rose-300 rounded text-xs">
                {deviceFormError}
              </div>
            )}

            <form onSubmit={handleRegisterDevice} className="space-y-3 mt-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Target Collector</label>
                <select
                  value={selectedCollectorId || ''}
                  onChange={(e) => setSelectedCollectorId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-slate-100"
                >
                  {collectors.map((c) => (
                    <option key={c.collector_id} value={c.collector_id}>
                      {c.name} ({c.collector_id}) - {c.status}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Device ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Router-HQ-01"
                  value={newDevice.device_id}
                  onChange={(e) => setNewDevice({ ...newDevice, device_id: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-slate-100 font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Device Name / Label</label>
                <input
                  type="text"
                  placeholder="Main Office Gateway Router"
                  value={newDevice.name}
                  onChange={(e) => setNewDevice({ ...newDevice, name: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-slate-100"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Device Type</label>
                  <select
                    value={newDevice.device_type}
                    onChange={(e) => setNewDevice({ ...newDevice, device_type: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-slate-100"
                  >
                    <option value="router">Router</option>
                    <option value="switch">Switch</option>
                    <option value="ap">Access Point (Wi-Fi)</option>
                    <option value="server">Server</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Protocol</label>
                  <select
                    value={newDevice.protocol}
                    onChange={(e) => {
                      const proto = e.target.value;
                      let p = 80;
                      if (proto === 'SNMP') p = 161;
                      else if (proto === 'RESTCONF') p = 443;
                      setNewDevice({ ...newDevice, protocol: proto, port: p });
                    }}
                    className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-slate-100"
                  >
                    <option value="TCP_PROBE">TCP Probe</option>
                    <option value="SNMP">SNMP v2c/v3</option>
                    <option value="RESTCONF">RESTCONF / REST</option>
                    <option value="WIFI_CONTROLLER">Wi-Fi Controller</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">LAN IP Address</label>
                  <input
                    type="text"
                    required
                    placeholder="192.168.1.1"
                    value={newDevice.ip}
                    onChange={(e) => setNewDevice({ ...newDevice, ip: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-slate-100 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Port</label>
                  <input
                    type="number"
                    value={newDevice.port}
                    onChange={(e) => setNewDevice({ ...newDevice, port: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-slate-100 font-mono"
                  />
                </div>
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowDeviceModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-bold"
                >
                  Save Device
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
