import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Router,
  Network,
  Wifi,
  Server,
  Database,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Layers,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react';

const BASELINES = {
  latency_ms: { label: 'Round-Trip Latency', baseline: 5.0, unit: 'ms', warn: 50.0, crit: 100.0 },
  jitter_ms: { label: 'Packet Jitter', baseline: 0.5, unit: 'ms', warn: 15.0, crit: 25.0 },
  packet_loss_pct: { label: 'Packet Loss', baseline: 0.0, unit: '%', warn: 1.0, crit: 5.0 },
  utilization_pct: { label: 'Link Utilization', baseline: 20.0, unit: '%', warn: 80.0, crit: 90.0 },
  queue_drops_per_sec: { label: 'Queue Discard Rate', baseline: 0.0, unit: 'pkts/s', warn: 5.0, crit: 20.0 },
  cpu_utilization_pct: { label: 'CPU Utilization', baseline: 25.0, unit: '%', warn: 80.0, crit: 90.0 },
  memory_utilization_pct: { label: 'Memory Usage', baseline: 40.0, unit: '%', warn: 80.0, crit: 90.0 },
  interface_crc_errors: { label: 'CRC Frame Errors', baseline: 0, unit: 'err/s', warn: 20, crit: 150 },
  interface_flaps: { label: 'Interface Flaps', baseline: 0, unit: 'flaps', warn: 1, crit: 3 },
  wifi_rssi_dbm: { label: 'Wi-Fi Signal (RSSI)', baseline: -55.0, unit: 'dBm', warn: -75.0, crit: -82.0, reverse: true },
  wifi_snr_db: { label: 'Wi-Fi SNR', baseline: 35.0, unit: 'dB', warn: 20.0, crit: 12.0, reverse: true },
  wifi_retry_pct: { label: '802.11 Retries', baseline: 2.0, unit: '%', warn: 15.0, crit: 25.0 },
  dns_response_ms: { label: 'DNS Query Response', baseline: 12.0, unit: 'ms', warn: 500.0, crit: 1500.0 },
  dhcp_pool_utilization_pct: { label: 'DHCP Pool Saturation', baseline: 45.0, unit: '%', warn: 85.0, crit: 95.0 },
};

export default function DeviceDetailsModal({
  isOpen,
  onClose,
  deviceNode,
  telemetryRecord,
  isImplicated = false,
}) {
  if (!isOpen || !deviceNode) return null;

  const data = deviceNode.data || {};
  const rec = telemetryRecord || {};

  const getDeviceIcon = () => {
    switch (data.device_type) {
      case 'router':
        return <Router className="w-6 h-6 text-cyan-400" />;
      case 'switch':
        return <Network className="w-6 h-6 text-blue-400" />;
      case 'ap':
        return <Wifi className="w-6 h-6 text-violet-400" />;
      case 'server':
        return data.id?.includes('DB') ? (
          <Database className="w-6 h-6 text-emerald-400" />
        ) : (
          <Server className="w-6 h-6 text-amber-400" />
        );
      default:
        return <Network className="w-6 h-6 text-slate-400" />;
    }
  };

  // Compile active metric comparison rows
  const comparisonRows = Object.keys(BASELINES)
    .map((key) => {
      const val = rec[key];
      if (val === undefined || val === null) return null;

      const conf = BASELINES[key];
      const isReverse = conf.reverse; // for RSSI/SNR where lower is worse
      const isCrit = isReverse ? val <= conf.crit : val >= conf.crit;
      const isWarn = isReverse ? val <= conf.warn && val > conf.crit : val >= conf.warn && val < conf.crit;

      return {
        key,
        label: conf.label,
        observed: val,
        baseline: conf.baseline,
        unit: conf.unit,
        isCrit,
        isWarn,
        isNominal: !isCrit && !isWarn,
      };
    })
    .filter(Boolean);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="w-full max-w-2xl bg-[#0c101c] border border-[#22314d] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#1f2c45] bg-[#0f1422]">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-[#141c2e] border border-[#223352]">
                {getDeviceIcon()}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-white">{data.label || deviceNode.id}</h3>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40 text-cyan-300">
                    {data.ip || '10.0.0.X'}
                  </span>
                  {isImplicated ? (
                    <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">
                      <AlertTriangle className="w-3 h-3" />
                      FAULT TARGET
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      <CheckCircle2 className="w-3 h-3" />
                      SLA NOMINAL
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Role: <strong className="text-slate-300">{data.role || 'Enterprise Network Node'}</strong> • Device Type: <span className="uppercase text-cyan-400">{data.device_type}</span>
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#1f2c45] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Telemetry Comparison Table */}
          <div className="p-6 overflow-y-auto space-y-4">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-[#1b253b] pb-2">
              <span className="font-bold text-slate-200">Observed Telemetry vs. Baseline SLA Bounds</span>
              <span>{comparisonRows.length} Monitored Dimensions</span>
            </div>

            {comparisonRows.length === 0 ? (
              <div className="text-center py-8 text-slate-500 font-mono text-xs">
                No telemetry counters loaded for this node in the current scenario.
              </div>
            ) : (
              <div className="space-y-2">
                {comparisonRows.map((row) => (
                  <div
                    key={row.key}
                    className={`p-3 rounded-xl border transition-all flex items-center justify-between ${
                      row.isCrit
                        ? 'bg-rose-950/25 border-rose-500/50 text-rose-200 shadow-sm shadow-rose-950/30'
                        : row.isWarn
                        ? 'bg-amber-950/20 border-amber-500/40 text-amber-200'
                        : 'bg-[#090d16] border-[#18233a] text-slate-300'
                    }`}
                  >
                    <div>
                      <div className="text-xs font-bold text-white flex items-center gap-2">
                        {row.label}
                        {row.isCrit && (
                          <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-rose-500/30 text-rose-300 border border-rose-500/50">
                            Critical Anomaly
                          </span>
                        )}
                        {row.isWarn && (
                          <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-amber-500/30 text-amber-300 border border-amber-500/50">
                            Elevated
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                        Baseline Expectation: {row.baseline} {row.unit}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className={`text-sm font-extrabold font-mono ${
                        row.isCrit ? 'text-rose-400' : row.isWarn ? 'text-amber-400' : 'text-emerald-400'
                      }`}>
                        {row.observed} <span className="text-xs font-normal text-slate-400">{row.unit}</span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500">
                        {row.isCrit ? 'Exceeds SLA threshold' : row.isWarn ? 'Approaching threshold' : 'Within normal limits'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-3 border-t border-[#1f2c45] bg-[#090d16] flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Node ID: <strong className="text-white">{deviceNode.id}</strong></span>
            <span>Canonical Telemetry Standard: <strong className="text-cyan-400">v1.0.0</strong></span>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

