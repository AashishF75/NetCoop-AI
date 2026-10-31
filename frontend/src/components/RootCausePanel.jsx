import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  ShieldAlert,
  Terminal,
  Copy,
  Check,
  ChevronRight,
  Sparkles,
  GitCompare,
  Info,
} from 'lucide-react';

export default function RootCausePanel({ report }) {
  const [copiedStep, setCopiedStep] = useState(null);

  if (!report) {
    return (
      <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-6 text-center text-slate-500 font-mono text-xs shadow-xl">
        Awaiting diagnosis execution. Select a scenario and click "Run Multi-Agent Diagnosis".
      </div>
    );
  }

  const {
    incident_id,
    status,
    suspected_root_cause,
    confidence,
    affected_devices = [],
    alternative_causes = [],
    recommended_actions = [],
    limitations = [],
    execution_time_ms,
  } = report;

  const confPercent = Math.round((confidence || 0) * 100);

  const getStatusBadge = () => {
    switch (status) {
      case 'CONFIRMED':
        return {
          bg: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
          icon: ShieldAlert,
          title: 'Root Cause Confirmed',
        };
      case 'SUSPECTED':
        return {
          bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
          icon: AlertTriangle,
          title: 'Suspected Fault',
        };
      case 'INCONCLUSIVE':
        return {
          bg: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
          icon: HelpCircle,
          title: 'Inconclusive (Data Gap)',
        };
      case 'HEALTHY':
        return {
          bg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
          icon: CheckCircle,
          title: 'Network Nominal',
        };
      default:
        return {
          bg: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
          icon: Info,
          title: status,
        };
    }
  };

  const statusConfig = getStatusBadge();
  const StatusIcon = statusConfig.icon;

  const copyCommand = (cmd, step) => {
    navigator.clipboard.writeText(cmd);
    setCopiedStep(step);
    setTimeout(() => setCopiedStep(null), 1800);
  };

  return (
    <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-5 shadow-xl space-y-5">
      {/* Top Banner: Root Cause & Confidence */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="rounded-xl p-4 bg-gradient-to-r from-[#131b2e] via-[#101726] to-[#0d121f] border border-[#22314d]"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2.5 py-1 rounded-md text-xs font-bold border flex items-center gap-1.5 ${statusConfig.bg}`}>
                <StatusIcon className="w-3.5 h-3.5" />
                {statusConfig.title}
              </span>
              <span className="text-xs font-mono text-slate-400">
                Incident #{incident_id}
              </span>
              <span className="text-xs font-mono text-cyan-400">
                {execution_time_ms} ms
              </span>
            </div>

            <h3 className="text-base sm:text-lg font-bold text-white tracking-tight leading-snug">
              {suspected_root_cause}
            </h3>

            {affected_devices.length > 0 && (
              <div className="flex items-center gap-2 mt-2 text-xs font-mono">
                <span className="text-slate-400">Implicated Nodes:</span>
                <div className="flex flex-wrap gap-1">
                  {affected_devices.map((dev) => (
                    <span
                      key={dev}
                      className="px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/30 text-rose-300 font-bold"
                    >
                      {dev}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Confidence Indicator Meter */}
          <div className="flex flex-col items-center justify-center p-3 rounded-xl bg-[#090d16] border border-[#1d273d] min-w-[110px]">
            <div className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-1">
              Confidence
            </div>
            <div className="text-2xl font-extrabold font-mono text-cyan-400">
              {confPercent}%
            </div>
            {/* Confidence Bar */}
            <div className="w-20 h-1.5 bg-slate-800 rounded-full mt-1.5 overflow-hidden">
              <div
                className={`h-full transition-all duration-700 ${
                  confPercent > 80 ? 'bg-cyan-400' : confPercent > 50 ? 'bg-amber-400' : 'bg-rose-400'
                }`}
                style={{ width: `${confPercent}%` }}
              ></div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Competing Root-Cause Hypotheses */}
      {alternative_causes.length > 0 && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-xs font-bold text-white uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <GitCompare className="w-4 h-4 text-amber-400" />
              Competing Hypotheses Evaluation
            </span>
            <span className="text-slate-400 font-mono text-[11px] font-normal">
              {alternative_causes.length} Ranked Hypotheses
            </span>
          </div>

          <div className="grid grid-cols-1 gap-2">
            {alternative_causes.slice(0, 3).map((hyp, index) => {
              const probPct = Math.round(hyp.probability * 100);
              const isValidated = hyp.status === 'VALIDATED';

              return (
                <motion.div
                  key={hyp.hypothesis_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`p-3 rounded-xl bg-[#0a0d16] border ${
                    isValidated ? 'border-amber-500/40 bg-amber-950/10' : 'border-[#1b253b]'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        Rank #{index + 1}
                      </span>
                      <h4 className="text-xs font-bold text-white">{hyp.name}</h4>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          isValidated ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {probPct}% Prob
                      </span>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 mb-2">{hyp.description}</p>

                  {/* Supporting / Contradicting Bullets */}
                  <div className="space-y-1 text-[10px] font-mono">
                    {hyp.supporting_evidence.map((sup, sIdx) => (
                      <div key={sIdx} className="text-emerald-400 flex items-center gap-1.5">
                        <span className="w-1 h-1 rounded-full bg-emerald-400"></span>
                        <span>PRO: {sup}</span>
                      </div>
                    ))}
                    {hyp.contradicting_evidence.map((con, cIdx) => (
                      <div key={cIdx} className="text-slate-400 flex items-center gap-1.5">
                        <span className="w-1 h-1 rounded-full bg-slate-500"></span>
                        <span>CON: {con}</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}

      {/* Actionable Remediation Runbooks */}
      {recommended_actions.length > 0 && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-xs font-bold text-white uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <Terminal className="w-4 h-4 text-emerald-400" />
              Actionable Remediation Runbook
            </span>
            <span className="text-slate-400 font-mono text-[11px] font-normal">
              {recommended_actions.length} Ordered Steps
            </span>
          </div>

          <div className="space-y-2">
            {recommended_actions.map((act) => {
              const isCopied = copiedStep === act.step;

              return (
                <div
                  key={act.step}
                  className="p-3 rounded-xl bg-[#0a0d16] border border-[#1b253b] hover:border-emerald-500/30 transition-all"
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-bold flex items-center justify-center">
                        {act.step}
                      </span>
                      <h4 className="text-xs font-bold text-white">{act.action}</h4>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800/40">
                        {act.target_device}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          act.risk_level === 'HIGH'
                            ? 'bg-rose-500/20 text-rose-300'
                            : act.risk_level === 'MEDIUM'
                            ? 'bg-amber-500/20 text-amber-300'
                            : 'bg-emerald-500/20 text-emerald-300'
                        }`}
                      >
                        {act.risk_level} RISK
                      </span>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-300 mb-2 leading-relaxed">{act.rationale}</p>

                  {act.command && (
                    <div className="relative group bg-[#06080e] rounded-lg p-2.5 border border-[#192235]">
                      <code className="text-xs font-mono text-emerald-400 block whitespace-pre-wrap">
                        {act.command}
                      </code>
                      <button
                        onClick={() => copyCommand(act.command, act.step)}
                        className="absolute top-2 right-2 p-1 rounded bg-[#131b2e] text-slate-400 hover:text-white border border-[#202d47]"
                        title="Copy command to clipboard"
                      >
                        {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Diagnostic Limitations Notice (if any) */}
      {limitations.length > 0 && (
        <div className="p-3 rounded-xl bg-purple-950/20 border border-purple-800/40 text-xs">
          <div className="flex items-center gap-2 text-purple-300 font-bold mb-1">
            <Info className="w-4 h-4" />
            Diagnostic Limitations & Telemetry Caveats
          </div>
          <ul className="list-disc list-inside text-slate-300 space-y-1 font-mono text-[11px]">
            {limitations.map((lim, i) => (
              <li key={i}>{lim}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
