import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { fetchDigitalTwin } from '../api/client';

export default function DigitalTwinView({ onSelectDevice }) {
  const [snapshot, setSnapshot] = useState(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState('Core-Router-01');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadTwinData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDigitalTwin();
      setSnapshot(data);
      if (data.devices && data.devices.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(data.devices[0].device_id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load Digital Twin snapshot');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTwinData();
  }, []);

  const selectedDevice = snapshot?.devices?.find((d) => d.device_id === selectedDeviceId) || snapshot?.devices?.[0];

  const getStatusBadge = (status) => {
    if (status === 'OPTIMAL') {
      return <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">OPTIMAL</span>;
    }
    if (status === 'WARNING') {
      return <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">WARNING</span>;
    }
    return <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">CRITICAL</span>;
  };

  const getSlaBadge = (sla) => {
    if (sla === 'COMPLIANT') {
      return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950/40 text-emerald-400 border border-emerald-500/30">SLA COMPLIANT</span>;
    }
    if (sla === 'AT_RISK') {
      return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/40 text-amber-400 border border-amber-500/30">SLA AT RISK</span>;
    }
    return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-950/40 text-rose-400 border border-rose-500/30">SLA BREACHED</span>;
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-6">
      {/* Header & Mode Badge */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </span>
            <h2 className="text-lg font-bold text-slate-100">Network Digital Twin Environment</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time digital twin mirroring network topology, upstream/downstream service dependencies, and operational SLA adherence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-indigo-950/60 text-indigo-300 border border-indigo-500/40 shadow">
            🌐 BENCHMARK DIGITAL TWIN SIMULATION
          </span>
          <button
            onClick={loadTwinData}
            disabled={loading}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-all text-xs flex items-center gap-1"
          >
            <span>🔄</span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs">
          ⚠️ {error}
        </div>
      )}

      {loading && !snapshot ? (
        <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-2">
          <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs">Synchronizing Digital Twin telemetry state...</span>
        </div>
      ) : (
        <>
          {/* Global Digital Twin Metrics KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3.5 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-slate-500 block text-[10px] font-mono uppercase tracking-wider">Network Health Index</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className={`text-2xl font-black font-mono ${
                  (snapshot?.network_health_index || 0) >= 80 ? 'text-emerald-400' : 'text-amber-400'
                }`}>
                  {snapshot?.network_health_index || 0}%
                </span>
                <span className="text-[10px] text-slate-400">composite</span>
              </div>
            </div>

            <div className="p-3.5 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-slate-500 block text-[10px] font-mono uppercase tracking-wider">SLA Compliance Rate</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-black font-mono text-cyan-400">
                  {snapshot?.sla_compliance_pct || 0}%
                </span>
                <span className="text-[10px] text-slate-400">compliant nodes</span>
              </div>
            </div>

            <div className="p-3.5 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-slate-500 block text-[10px] font-mono uppercase tracking-wider">Active Device Incidents</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className={`text-2xl font-black font-mono ${
                  (snapshot?.active_incidents_count || 0) > 0 ? 'text-rose-400' : 'text-slate-400'
                }`}>
                  {snapshot?.active_incidents_count || 0}
                </span>
                <span className="text-[10px] text-slate-400">anomalous</span>
              </div>
            </div>

            <div className="p-3.5 bg-slate-950/80 rounded-xl border border-slate-800">
              <span className="text-slate-500 block text-[10px] font-mono uppercase tracking-wider">Monitored Digital Nodes</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-black font-mono text-slate-200">
                  {snapshot?.devices?.length || 8}
                </span>
                <span className="text-[10px] text-slate-400">live agents</span>
              </div>
            </div>
          </div>

          {/* Main Twin Layout: Devices Grid on Left, Selected Device Deep Inspector on Right */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Device Roster & Status Grid */}
            <div className="lg:col-span-5 space-y-3">
              <label className="block text-xs font-mono uppercase text-slate-400 tracking-wider">
                Digital Twin Nodes & Dependency Topology:
              </label>
              <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
                {snapshot?.devices?.map((dev) => {
                  const isSelected = dev.device_id === selectedDeviceId;
                  return (
                    <motion.div
                      key={dev.device_id}
                      whileHover={{ scale: 1.01 }}
                      onClick={() => setSelectedDeviceId(dev.device_id)}
                      className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                        isSelected
                          ? 'bg-indigo-950/50 border-indigo-500 shadow-md shadow-indigo-900/20'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100 text-xs">{dev.name}</span>
                          <span className="text-[10px] font-mono text-slate-500">({dev.device_id})</span>
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                          <span>{dev.role}</span>
                          <span className="text-slate-600">•</span>
                          <span className="font-mono text-slate-400">{dev.ip}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-right">
                        <div>
                          <span className={`block font-mono font-bold text-xs ${
                            dev.health_score >= 80 ? 'text-emerald-400' : 'text-amber-400'
                          }`}>
                            {dev.health_score}%
                          </span>
                          <span className="text-[9px] text-slate-500 uppercase">Health</span>
                        </div>
                        {getStatusBadge(dev.status)}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>

            {/* Selected Device Deep Inspector */}
            <div className="lg:col-span-7 bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-5">
              {selectedDevice ? (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-slate-100">{selectedDevice.name}</h3>
                        <span className="font-mono text-xs text-indigo-400">[{selectedDevice.device_id}]</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">Role: {selectedDevice.role} | IP: {selectedDevice.ip}</p>
                    </div>

                    <div className="flex items-center gap-2">
                      {getStatusBadge(selectedDevice.status)}
                      {getSlaBadge(selectedDevice.sla_status)}
                    </div>
                  </div>

                  {/* Dependency Chain */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
                    <div>
                      <span className="text-slate-500 block text-[10px] font-mono uppercase mb-1">⬆️ Upstream Dependencies</span>
                      {selectedDevice.upstream_dependencies.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {selectedDevice.upstream_dependencies.map((u) => (
                            <button
                              key={u}
                              onClick={() => setSelectedDeviceId(u)}
                              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 font-mono text-[11px] transition-all"
                            >
                              {u}
                            </button>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-500 italic text-[11px]">Root Core Node (No Upstream)</span>
                      )}
                    </div>

                    <div>
                      <span className="text-slate-500 block text-[10px] font-mono uppercase mb-1">⬇️ Downstream Dependencies</span>
                      {selectedDevice.downstream_dependencies.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {selectedDevice.downstream_dependencies.map((d) => (
                            <button
                              key={d}
                              onClick={() => setSelectedDeviceId(d)}
                              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 font-mono text-[11px] transition-all"
                            >
                              {d}
                            </button>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-500 italic text-[11px]">Edge Leaf Node</span>
                      )}
                    </div>
                  </div>

                  {/* Active Anomalies List */}
                  {selectedDevice.active_anomalies.length > 0 ? (
                    <div className="p-3 bg-rose-950/20 border border-rose-500/30 rounded-lg space-y-1">
                      <span className="text-xs font-bold text-rose-400 block">⚠️ Active Domain Anomalies Detected:</span>
                      <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
                        {selectedDevice.active_anomalies.map((anom, i) => (
                          <li key={i}>{anom}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div className="p-2.5 bg-emerald-950/20 border border-emerald-500/20 rounded-lg text-xs text-emerald-400 flex items-center gap-2">
                      <span>✅</span>
                      <span>All telemetry counters within nominal operating parameters.</span>
                    </div>
                  )}

                  {/* Telemetry vs Baseline SLA Bounds Table */}
                  <div>
                    <h4 className="text-xs font-mono uppercase text-slate-400 tracking-wider mb-2">
                      Live Telemetry vs Baseline SLA Bounds
                    </h4>
                    <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/40">
                      <table className="w-full text-left text-xs text-slate-300 border-collapse">
                        <thead>
                          <tr className="bg-slate-900 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                            <th className="p-2.5">Metric Dimension</th>
                            <th className="p-2.5">Current Telemetry</th>
                            <th className="p-2.5">Baseline SLA Bound</th>
                            <th className="p-2.5">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/80 font-mono text-[11px]">
                          {Object.entries(selectedDevice.current_telemetry || {})
                            .filter(([_, val]) => val !== null && val !== undefined)
                            .map(([metric, val]) => {
                              const bound = selectedDevice.baseline_sla?.[metric];
                              const maxSla = bound?.max_sla;
                              const minSla = bound?.min_sla;
                              const unit = bound?.unit || '';

                              let isBreached = false;
                              if (maxSla !== undefined && typeof val === 'number') {
                                isBreached = val > maxSla;
                              }
                              if (minSla !== undefined && typeof val === 'number') {
                                isBreached = val < minSla;
                              }

                              return (
                                <tr key={metric} className="hover:bg-slate-800/40">
                                  <td className="p-2.5 text-slate-300 font-sans font-medium">
                                    {metric.replace(/_/g, ' ')}
                                  </td>
                                  <td className="p-2.5 font-bold text-slate-100">
                                    {val} {unit}
                                  </td>
                                  <td className="p-2.5 text-slate-400">
                                    {maxSla !== undefined && `≤ ${maxSla} ${unit}`}
                                    {minSla !== undefined && `≥ ${minSla} ${unit}`}
                                    {!maxSla && !minSla && 'Nominal'}
                                  </td>
                                  <td className="p-2.5">
                                    {isBreached ? (
                                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                        BREACH
                                      </span>
                                    ) : (
                                      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                        PASS
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              ) : (
                <div className="py-12 text-center text-slate-500 text-xs">
                  Select a digital twin node to inspect telemetry and dependency tree.
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

