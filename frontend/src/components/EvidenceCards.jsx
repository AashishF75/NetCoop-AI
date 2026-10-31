import React from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, AlertTriangle, Info, Database, Layers } from 'lucide-react';

export default function EvidenceCards({ evidenceItems = [] }) {
  if (!evidenceItems || evidenceItems.length === 0) {
    return (
      <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-4 text-center text-slate-500 font-mono text-xs">
        No anomalous telemetry evidence detected. All monitored metrics within baseline SLA limits.
      </div>
    );
  }

  const getSeverityBadge = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return {
          bg: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
          icon: ShieldAlert,
        };
      case 'WARNING':
        return {
          bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
          icon: AlertTriangle,
        };
      default:
        return {
          bg: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
          icon: Info,
        };
    }
  };

  return (
    <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-4 shadow-xl">
      <div className="flex items-center justify-between gap-2 mb-3.5 border-b border-[#1f293d] pb-2.5">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white tracking-wide">Structured Diagnostic Evidence Ledger</h2>
        </div>
        <span className="text-xs font-mono text-cyan-400">
          {evidenceItems.length} Evidence Artifacts
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {evidenceItems.map((item, idx) => {
          const sev = getSeverityBadge(item.severity);
          const SevIcon = sev.icon;

          return (
            <motion.div
              key={`${item.device_id}-${item.metric}-${idx}`}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.05 }}
              whileHover={{ y: -2 }}
              className="p-3.5 rounded-xl bg-[#0a0d16] border border-[#1b253b] hover:border-cyan-500/40 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[11px] font-bold font-mono text-cyan-300 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800/40">
                    {item.device_id}
                  </span>
                  <span className={`flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded border ${sev.bg}`}>
                    <SevIcon className="w-3 h-3" />
                    {item.severity}
                  </span>
                </div>

                <div className="text-xs font-semibold text-slate-200 mb-1">
                  {item.summary}
                </div>
              </div>

              <div className="mt-2.5 pt-2 border-t border-[#1b253b] flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>Observed: <strong className="text-white">{String(item.observed_value)} {item.unit}</strong></span>
                {item.threshold && <span>Threshold: {String(item.threshold)}</span>}
                <span className="text-cyan-400">{item.agent_id}</span>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
