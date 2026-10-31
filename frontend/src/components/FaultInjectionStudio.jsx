import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { injectFaultAndDiagnose } from '../api/client';

const DEFAULT_INJECTION = {
  device_id: 'Core-Router-01',
  cpu_utilization_pct: 99.4,
  latency_ms: 115.0,
  packet_loss_pct: 4.2,
  utilization_pct: 14.0,
  queue_drops_per_sec: 0.0,
  interface_crc_errors: 0,
  wifi_rssi_dbm: -55.0,
  dns_response_ms: 12.0,
  dropped_fields: [],
};

const PRESETS = [
  {
    name: 'Control Plane CPU Saturation',
    description: 'Elevated CPU (99.4%) with normal link utilization (14%) and 0 queue drops.',
    values: {
      device_id: 'Core-Router-01',
      cpu_utilization_pct: 99.4,
      latency_ms: 115.0,
      packet_loss_pct: 4.2,
      utilization_pct: 14.0,
      queue_drops_per_sec: 0.0,
      interface_crc_errors: 0,
      wifi_rssi_dbm: -55.0,
      dns_response_ms: 12.0,
      dropped_fields: [],
    },
  },
  {
    name: 'Egress Link Buffer Congestion',
    description: 'Trunk saturated at 98% with 84 pkts/s queue drops and 142ms latency.',
    values: {
      device_id: 'Core-Router-01',
      cpu_utilization_pct: 35.0,
      latency_ms: 142.0,
      packet_loss_pct: 6.5,
      utilization_pct: 98.0,
      queue_drops_per_sec: 84.0,
      interface_crc_errors: 0,
      wifi_rssi_dbm: -55.0,
      dns_response_ms: 12.0,
      dropped_fields: [],
    },
  },
  {
    name: 'Optical Transceiver CRC Degradation',
    description: 'Degraded SFP optic causing 450 CRC errors/sec on switch uplink.',
    values: {
      device_id: 'Agg-Switch-01',
      cpu_utilization_pct: 22.0,
      latency_ms: 18.0,
      packet_loss_pct: 5.2,
      utilization_pct: 35.0,
      queue_drops_per_sec: 0.0,
      interface_crc_errors: 450,
      wifi_rssi_dbm: -55.0,
      dns_response_ms: 12.0,
      dropped_fields: [],
    },
  },
  {
    name: 'Wi-Fi Edge Signal Path Loss',
    description: 'Severe client attenuation (-86 dBm RSSI) and 42% frame retries.',
    values: {
      device_id: 'AP-02',
      cpu_utilization_pct: 18.0,
      latency_ms: 32.0,
      packet_loss_pct: 4.8,
      utilization_pct: 25.0,
      queue_drops_per_sec: 0.0,
      interface_crc_errors: 0,
      wifi_rssi_dbm: -86.0,
      dns_response_ms: 12.0,
      dropped_fields: [],
    },
  },
  {
    name: 'Missing Telemetry Simulation',
    description: 'Drop queue drop counters and CPU utilization to test insufficient evidence handling.',
    values: {
      device_id: 'Core-Router-01',
      cpu_utilization_pct: null,
      latency_ms: 85.0,
      packet_loss_pct: 3.5,
      utilization_pct: 88.0,
      queue_drops_per_sec: null,
      interface_crc_errors: 0,
      wifi_rssi_dbm: -55.0,
      dns_response_ms: 12.0,
      dropped_fields: ['cpu_utilization_pct', 'queue_drops_per_sec'],
    },
  },
];

export default function FaultInjectionStudio({ onDiagnosisComplete }) {
  const [params, setParams] = useState(DEFAULT_INJECTION);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState(null);
  const [successResult, setSuccessResult] = useState(null);

  const applyPreset = (preset) => {
    setParams({ ...preset.values });
    setSuccessResult(null);
  };

  const resetToBaseline = () => {
    setParams({
      device_id: 'Core-Router-01',
      cpu_utilization_pct: 18.0,
      latency_ms: 4.2,
      packet_loss_pct: 0.0,
      utilization_pct: 25.0,
      queue_drops_per_sec: 0.0,
      interface_crc_errors: 0,
      wifi_rssi_dbm: -55.0,
      dns_response_ms: 12.0,
      dropped_fields: [],
    });
    setSuccessResult(null);
  };

  const handleFieldDropToggle = (fieldName) => {
    setParams((prev) => {
      const isDropped = prev.dropped_fields.includes(fieldName);
      const newDropped = isDropped
        ? prev.dropped_fields.filter((f) => f !== fieldName)
        : [...prev.dropped_fields, fieldName];
      return { ...prev, dropped_fields: newDropped };
    });
  };

  const handleRunInjectedDiagnosis = async () => {
    setExecuting(true);
    setError(null);
    try {
      const result = await injectFaultAndDiagnose(params);
      setSuccessResult(result);
      if (onDiagnosisComplete) {
        onDiagnosisComplete(result);
      }
    } catch (err) {
      setError(err.message || 'Fault injection failed');
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </span>
            <h2 className="text-lg font-bold text-slate-100">Interactive Fault Injection & Scenario Builder</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Induce controlled multi-layer telemetry anomalies, drop dimensions to test agent resilience, and trigger real-time multi-agent reasoning.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={resetToBaseline}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs rounded-lg transition-all"
          >
            Reset to Nominal Baseline
          </button>
          <button
            data-testid="inject-run-btn"
            onClick={handleRunInjectedDiagnosis}
            disabled={executing}
            className="px-4 py-2 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-semibold text-xs rounded-lg shadow-lg shadow-amber-900/30 flex items-center gap-2 transition-all disabled:opacity-50"
          >
            {executing ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Swarm Investigating Injected Fault...</span>
              </>
            ) : (
              <>
                <span>⚡</span>
                <span>Run Multi-Agent Diagnosis</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs">
          ⚠️ {error}
        </div>
      )}

      {/* Preset Fault Quick-Launch Buttons */}
      <div>
        <label className="block text-xs font-mono uppercase text-slate-400 tracking-wider mb-2">
          Quick Fault Injection Presets:
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {PRESETS.map((p) => (
            <button
              key={p.name}
              onClick={() => applyPreset(p)}
              className="p-3 bg-slate-950/70 hover:bg-slate-800/80 border border-slate-800 hover:border-amber-500/50 rounded-xl text-left transition-all group flex flex-col justify-between"
            >
              <div>
                <span className="font-semibold text-xs text-slate-200 group-hover:text-amber-300 block mb-1">
                  {p.name}
                </span>
                <span className="text-[10px] text-slate-400 line-clamp-2 leading-tight">
                  {p.description}
                </span>
              </div>
              <span className="text-[9px] font-mono text-cyan-400 mt-2 block">
                Target: {p.values.device_id}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Interactive Controls Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 bg-slate-950/70 p-5 rounded-xl border border-slate-800">
        {/* Column 1: Target Device & Infrastructure Metrics */}
        <div className="space-y-4">
          <h3 className="text-xs font-mono uppercase text-cyan-400 tracking-wider border-b border-slate-800/80 pb-2">
            1. Target Node & Compute
          </h3>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Target Network Device</label>
            <select
              value={params.device_id}
              onChange={(e) => setParams({ ...params, device_id: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
            >
              <option value="Core-Router-01">Core-Router-01 (Core Gateway)</option>
              <option value="Agg-Switch-01">Agg-Switch-01 (Distribution Switch)</option>
              <option value="Edge-Switch-01">Edge-Switch-01 (Access Switch)</option>
              <option value="AP-02">AP-02 (Enterprise Wi-Fi AP)</option>
              <option value="DNS-Server-01">DNS-Server-01 (Core Infrastructure)</option>
            </select>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">CPU Utilization (%)</span>
              <span className="font-mono font-bold text-amber-400">{params.cpu_utilization_pct ?? 'DROPPED'}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="0.5"
              value={params.cpu_utilization_pct || 0}
              disabled={params.dropped_fields.includes('cpu_utilization_pct')}
              onChange={(e) => setParams({ ...params, cpu_utilization_pct: parseFloat(e.target.value) })}
              className="w-full accent-amber-500 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Interface CRC Errors (/sec)</span>
              <span className="font-mono font-bold text-rose-400">{params.interface_crc_errors} err/s</span>
            </div>
            <input
              type="range"
              min="0"
              max="800"
              step="10"
              value={params.interface_crc_errors || 0}
              onChange={(e) => setParams({ ...params, interface_crc_errors: parseInt(e.target.value, 10) })}
              className="w-full accent-rose-500 cursor-pointer"
            />
          </div>
        </div>

        {/* Column 2: Traffic Dynamics & Queues */}
        <div className="space-y-4">
          <h3 className="text-xs font-mono uppercase text-cyan-400 tracking-wider border-b border-slate-800/80 pb-2">
            2. Traffic Dynamics & Latency
          </h3>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Round-Trip Latency (ms)</span>
              <span className="font-mono font-bold text-cyan-400">{params.latency_ms} ms</span>
            </div>
            <input
              type="range"
              min="1"
              max="300"
              step="1"
              value={params.latency_ms || 4}
              onChange={(e) => setParams({ ...params, latency_ms: parseFloat(e.target.value) })}
              className="w-full accent-cyan-500 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Link Bandwidth Utilization (%)</span>
              <span className="font-mono font-bold text-indigo-400">{params.utilization_pct}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={params.utilization_pct || 14}
              onChange={(e) => setParams({ ...params, utilization_pct: parseFloat(e.target.value) })}
              className="w-full accent-indigo-500 cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Egress Queue Drops (pkts/s)</span>
              <span className="font-mono font-bold text-purple-400">{params.queue_drops_per_sec ?? 'DROPPED'} pkts/s</span>
            </div>
            <input
              type="range"
              min="0"
              max="200"
              step="1"
              value={params.queue_drops_per_sec || 0}
              disabled={params.dropped_fields.includes('queue_drops_per_sec')}
              onChange={(e) => setParams({ ...params, queue_drops_per_sec: parseFloat(e.target.value) })}
              className="w-full accent-purple-500 cursor-pointer"
            />
          </div>
        </div>

        {/* Column 3: Edge RF & Missing Dimension Simulator */}
        <div className="space-y-4">
          <h3 className="text-xs font-mono uppercase text-cyan-400 tracking-wider border-b border-slate-800/80 pb-2">
            3. Edge RF & Telemetry Dropping
          </h3>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Wi-Fi RSSI (dBm)</span>
              <span className="font-mono font-bold text-emerald-400">{params.wifi_rssi_dbm} dBm</span>
            </div>
            <input
              type="range"
              min="-95"
              max="-30"
              step="1"
              value={params.wifi_rssi_dbm || -55}
              onChange={(e) => setParams({ ...params, wifi_rssi_dbm: parseFloat(e.target.value) })}
              className="w-full accent-emerald-500 cursor-pointer"
            />
          </div>

          {/* Missing Telemetry Simulator Checkboxes */}
          <div className="pt-2">
            <span className="text-slate-400 text-xs font-semibold block mb-2">Simulate Missing Telemetry Fields:</span>
            <div className="space-y-1.5 text-xs text-slate-300">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={params.dropped_fields.includes('cpu_utilization_pct')}
                  onChange={() => handleFieldDropToggle('cpu_utilization_pct')}
                  className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                />
                <span>Drop CPU Utilization Counter</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={params.dropped_fields.includes('queue_drops_per_sec')}
                  onChange={() => handleFieldDropToggle('queue_drops_per_sec')}
                  className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                />
                <span>Drop Egress Queue Drops Counter</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={params.dropped_fields.includes('interface_crc_errors')}
                  onChange={() => handleFieldDropToggle('interface_crc_errors')}
                  className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                />
                <span>Drop Interface CRC Errors Counter</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Success Banner if Injected Diagnosis Completed */}
      {successResult && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="p-4 bg-emerald-950/30 border border-emerald-500/40 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs"
        >
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span className="font-bold text-slate-100">Diagnosis Evaluated for Injected Scenario:</span>
              <span className="text-amber-300 font-bold">{successResult.suspected_root_cause}</span>
            </div>
            <p className="text-slate-400 mt-0.5">
              Incident ID: {successResult.incident_id} | Confidence: {Math.round(successResult.confidence * 100)}% | Status: {successResult.status}
            </p>
          </div>

          <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full font-mono text-[11px]">
            Active in Operations Dashboard
          </span>
        </motion.div>
      )}
    </div>
  );
}
