import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ListFilter,
  Download,
  Upload,
  Play,
  FileSpreadsheet,
  FileCode,
  Sparkles,
  AlertOctagon,
  Wifi,
  Network,
  Cpu,
  Server,
  HelpCircle,
  ShieldAlert,
} from 'lucide-react';
import { getExportUrl } from '../api/client';

const SCENARIO_ICONS = {
  normal_network: Sparkles,
  link_congestion: Network,
  weak_wifi_signal: Wifi,
  interface_fault: AlertOctagon,
  dns_dhcp_failure: Server,
  missing_telemetry: HelpCircle,
  incompatible_agent_messages: ShieldAlert,
  conflicting_evidence: Cpu,
};

export default function ScenarioSelector({
  scenarios = [],
  selectedScenarioId,
  onSelectScenario,
  onCustomTelemetrySubmit,
  isDiagnosing,
}) {
  const [activeTab, setActiveTab] = useState('catalog'); // 'catalog' | 'custom'
  const [customFormat, setCustomFormat] = useState('csv');
  const [customText, setCustomText] = useState('');

  const sampleCsv = `device_id,latency_ms,packet_loss_pct,cpu_utilization_pct,queue_drops_per_sec
Core-Router-01,135.0,7.2,32.0,88.0
Agg-Switch-01,130.0,6.5,29.0,82.0
Edge-Switch-01,140.0,7.0,18.0,0.0`;

  const sampleJson = `[
  {
    "device_id": "AP-02",
    "device_type": "ap",
    "wifi_rssi_dbm": -88.0,
    "wifi_snr_db": 8.5,
    "wifi_retry_pct": 48.0,
    "latency_ms": 125.0
  }
]`;

  const handleCustomSubmit = () => {
    if (!customText.trim()) return;
    onCustomTelemetrySubmit({ rawContent: customText, dataFormat: customFormat });
  };

  const loadSample = () => {
    setCustomText(customFormat === 'csv' ? sampleCsv : sampleJson);
  };

  return (
    <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-4 shadow-xl">
      {/* Tab Switcher */}
      <div className="flex items-center justify-between gap-3 mb-3.5 border-b border-[#1f293d] pb-2.5">
        <div className="flex items-center gap-2">
          <ListFilter className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white tracking-wide">Evaluation Scenario Benchmark Suite</h2>
        </div>

        <div className="flex items-center gap-1 bg-[#0a0d16] p-1 rounded-xl border border-[#1b2438] text-xs font-medium">
          <button
            onClick={() => setActiveTab('catalog')}
            className={`px-3 py-1 rounded-lg transition-all ${
              activeTab === 'catalog'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Benchmark Scenarios (8)
          </button>
          <button
            onClick={() => setActiveTab('custom')}
            className={`px-3 py-1 rounded-lg transition-all ${
              activeTab === 'custom'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Custom Ingestion (CSV / JSON)
          </button>
        </div>
      </div>

      {activeTab === 'catalog' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {scenarios.map((sc) => {
            const isSelected = selectedScenarioId === sc.id;
            const Icon = SCENARIO_ICONS[sc.id] || Network;

            return (
              <motion.div
                key={sc.id}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                onClick={() => onSelectScenario(sc.id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'bg-cyan-950/40 border-cyan-400 shadow-md shadow-cyan-500/10'
                    : 'bg-[#0a0d16] border-[#1b253b] hover:border-[#2b3c61]'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <div className={`p-1.5 rounded-lg ${isSelected ? 'bg-cyan-500 text-black' : 'bg-[#151c2e] text-cyan-400'}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        {sc.category}
                      </span>
                    </div>

                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        sc.severity === 'CRITICAL'
                          ? 'bg-rose-500/20 text-rose-300'
                          : sc.severity === 'HIGH'
                          ? 'bg-amber-500/20 text-amber-300'
                          : sc.severity === 'NORMAL'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : 'bg-cyan-500/20 text-cyan-300'
                      }`}
                    >
                      {sc.severity}
                    </span>
                  </div>

                  <h3 className={`text-xs font-bold mb-1 leading-tight ${isSelected ? 'text-cyan-300' : 'text-white'}`}>
                    {sc.name}
                  </h3>

                  <p className="text-[11px] text-slate-400 line-clamp-2 mb-2 leading-snug">
                    {sc.description}
                  </p>
                </div>

                {/* Export Buttons */}
                <div className="flex items-center justify-between pt-2 border-t border-[#1b253b] text-[10px] font-mono">
                  <span className="text-slate-400">Export:</span>
                  <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <a
                      href={getExportUrl(sc.id, 'json')}
                      download
                      className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#162035] hover:bg-cyan-900/60 text-cyan-300 hover:text-white"
                      title="Download JSON Telemetry"
                    >
                      <FileCode className="w-3 h-3" />
                      <span>JSON</span>
                    </a>
                    <a
                      href={getExportUrl(sc.id, 'csv')}
                      download
                      className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#162035] hover:bg-cyan-900/60 text-cyan-300 hover:text-white"
                      title="Download CSV Telemetry"
                    >
                      <FileSpreadsheet className="w-3 h-3" />
                      <span>CSV</span>
                    </a>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      ) : (
        /* Custom Ingestion Tab */
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-300 font-medium">Input Format:</span>
              <button
                onClick={() => setCustomFormat('csv')}
                className={`px-2.5 py-1 rounded-lg font-mono text-xs ${
                  customFormat === 'csv' ? 'bg-cyan-500 text-black font-bold' : 'bg-slate-800 text-slate-400'
                }`}
              >
                CSV
              </button>
              <button
                onClick={() => setCustomFormat('json')}
                className={`px-2.5 py-1 rounded-lg font-mono text-xs ${
                  customFormat === 'json' ? 'bg-cyan-500 text-black font-bold' : 'bg-slate-800 text-slate-400'
                }`}
              >
                JSON
              </button>
            </div>

            <button
              onClick={loadSample}
              className="text-xs text-cyan-400 hover:underline font-mono"
            >
              Load Sample Telemetry
            </button>
          </div>

          <textarea
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder={
              customFormat === 'csv'
                ? "Paste custom CSV here (e.g. device_id,latency_ms,packet_loss_pct,cpu_utilization_pct)..."
                : "Paste custom JSON telemetry array here..."
            }
            rows={5}
            className="w-full bg-[#0a0d16] border border-[#1b253b] focus:border-cyan-500 rounded-xl p-3 font-mono text-xs text-slate-200 outline-none resize-none"
          />

          <div className="flex justify-end">
            <button
              disabled={isDiagnosing || !customText.trim()}
              onClick={handleCustomSubmit}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-cyan-500/20"
            >
              <Upload className="w-4 h-4" />
              <span>Ingest & Run Diagnosis</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
