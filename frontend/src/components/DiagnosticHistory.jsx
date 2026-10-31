import React from 'react';
import { History, Clock, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function DiagnosticHistory({ history = [], onSelectHistoryItem, activeIncidentId }) {
  if (!history || history.length === 0) {
    return (
      <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-4 text-center text-slate-500 font-mono text-xs">
        No past diagnosis runs recorded in this session.
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-4 shadow-xl">
      <div className="flex items-center justify-between gap-2 mb-3.5 border-b border-[#1f293d] pb-2.5">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white tracking-wide">Diagnostic Run Timeline</h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          {history.length} Incident Runs Recorded
        </span>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {history.map((item, idx) => {
          const isActive = item.incident_id === activeIncidentId;
          const conf = Math.round((item.confidence || 0) * 100);

          return (
            <button
              key={`${item.incident_id}-${idx}`}
              onClick={() => onSelectHistoryItem(item)}
              className={`p-2.5 rounded-xl border text-left min-w-[210px] transition-all cursor-pointer flex-shrink-0 ${
                isActive
                  ? 'bg-cyan-950/40 border-cyan-400 shadow-md shadow-cyan-500/10'
                  : 'bg-[#0a0d16] border-[#1b253b] hover:border-[#2b3c61]'
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-xs font-mono font-bold text-cyan-300">
                  #{item.incident_id}
                </span>
                <span
                  className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                    item.status === 'CONFIRMED'
                      ? 'bg-rose-500/20 text-rose-300'
                      : item.status === 'HEALTHY'
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : 'bg-amber-500/20 text-amber-300'
                  }`}
                >
                  {item.status}
                </span>
              </div>

              <div className="text-xs font-bold text-white truncate mb-1">
                {item.suspected_root_cause}
              </div>

              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>Conf: <strong className="text-cyan-400">{conf}%</strong></span>
                <span>{item.execution_time_ms} ms</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
