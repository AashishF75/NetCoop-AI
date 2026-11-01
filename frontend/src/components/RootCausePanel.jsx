import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  ShieldAlert,
  Terminal,
  Copy,
  Check,
  GitCompare,
  Info,
  ArrowRight,
  Flame,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

export default function RootCausePanel({ report }) {
  const [copiedStep, setCopiedStep] = useState(null);

  if (!report) {
    return (
      <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-6 text-center text-slate-400 font-mono text-xs">
        Awaiting diagnosis execution. Select a scenario or run autonomous diagnosis.
      </div>
    );
  }

  const {
    status,
    suspected_root_cause,
    confidence,
    affected_devices = [],
    alternative_causes = [],
    recommended_actions = [],
    fault_propagation_paths = [],
    limitations = [],
    missing_telemetry = [],
    investigation_explanation,
  } = report;

  const protocol_rejection_confidence = report.protocol_rejection_confidence;
  const conflict_status = report.conflict_status || investigation_explanation?.conflict_status;
  const resolved_conflict_details = report.resolved_conflict_details || investigation_explanation?.resolved_conflict_details;

  const confPercent = Math.round((confidence || 0) * 100);

  const getStatusBadge = () => {
    switch (status) {
      case 'CONFIRMED':
        return {
          bg: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
          icon: ShieldAlert,
          title: 'Root Cause Confirmed',
        };
      case 'SUSPECTED':
        return {
          bg: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
          icon: AlertTriangle,
          title: 'Suspected Fault',
        };
      case 'INCONCLUSIVE':
        return {
          bg: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
          icon: HelpCircle,
          title: 'Inconclusive (Data Gap)',
        };
      case 'HEALTHY':
        return {
          bg: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
          icon: CheckCircle,
          title: 'Network Nominal',
        };
      default:
        return {
          bg: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
          icon: Info,
          title: status,
        };
    }
  };

  const statusConfig = getStatusBadge();
  const StatusIcon = statusConfig.icon;

  const copyCommand = (cmd, step) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(cmd).catch(() => {});
    }
    setCopiedStep(step);
    setTimeout(() => setCopiedStep(null), 1800);
  };

  const getHypothesisBadge = (statusStr) => {
    const s = (statusStr || '').toUpperCase();
    if (s === 'CONFIRMED' || s === 'VALIDATED') {
      return { bg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', icon: CheckCircle2, text: 'CONFIRMED' };
    }
    if (s === 'REJECTED' || s === 'REFUTED') {
      return { bg: 'bg-rose-500/20 text-rose-300 border-rose-500/30', icon: XCircle, text: 'DISQUALIFIED' };
    }
    if (s === 'NOT EVALUATED' || s === 'NOT_EVALUATED' || s === 'UNKNOWN' || s === 'UNRESOLVED') {
      return { bg: 'bg-slate-700/40 text-slate-400 border-slate-600/40', icon: HelpCircle, text: 'NOT EVALUATED' };
    }
    return { bg: 'bg-amber-500/20 text-amber-300 border-amber-500/30', icon: AlertTriangle, text: 'COMPETING' };
  };

  return (
    <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-5 shadow-md space-y-4">
      {/* Primary Root Cause Banner */}
      <div className="rounded-lg bg-slate-950 p-4 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1.5 flex-1">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-0.5 rounded-full border ${statusConfig.bg}`}>
              <StatusIcon className="w-3.5 h-3.5" />
              {statusConfig.title}
            </span>
            <span className="text-xs font-mono text-slate-400">Multi-Agent Consensus</span>
          </div>

          <h3 className="text-lg font-bold text-white tracking-tight">
            {suspected_root_cause}
          </h3>

          {/* Implicated Devices */}
          {affected_devices.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono pt-0.5">
              <span className="text-slate-400">Implicated Nodes:</span>
              {affected_devices.map((dev) => (
                <span
                  key={dev}
                  className="px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/30 text-rose-300 font-semibold"
                >
                  {dev}
                </span>
              ))}
            </div>
          )}

          {/* Fault Propagation Path */}
          {fault_propagation_paths && fault_propagation_paths.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono pt-0.5">
              <span className="text-amber-400 font-semibold flex items-center gap-1">
                <Flame className="w-3.5 h-3.5 text-amber-400" />
                Propagation Path:
              </span>
              <div className="flex items-center gap-1 text-slate-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                {fault_propagation_paths[0].map((node, i) => (
                  <React.Fragment key={node}>
                    <span className="font-semibold text-slate-100">{node}</span>
                    {i < fault_propagation_paths[0].length - 1 && (
                      <ArrowRight className="w-3 h-3 text-amber-400" />
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Confidence Meter */}
        <div className="flex flex-col items-center justify-center p-3 rounded-lg bg-slate-900 border border-slate-800 min-w-[120px]">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Confidence
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400">
            {confPercent}%
          </div>
          <div className="w-20 h-1.5 bg-slate-800 rounded-full mt-1.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                confPercent >= 80 ? 'bg-cyan-400' : confPercent >= 50 ? 'bg-amber-400' : 'bg-rose-400'
              }`}
              style={{ width: `${confPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Protocol Rejection vs Network Diagnosis Confidence Badge (Fix 2) */}
      {protocol_rejection_confidence && (
        <div className="rounded-lg bg-purple-950/25 border border-purple-500/30 p-3.5 space-y-1.5 text-xs font-mono">
          <div className="flex items-center justify-between">
            <span className="text-purple-300 font-bold uppercase tracking-wider flex items-center gap-1.5">
              <HelpCircle className="w-4 h-4 text-purple-400" />
              Protocol Interoperability Rejection
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
              {Math.round(protocol_rejection_confidence * 100)}% Rejection Certainty
            </span>
          </div>
          <p className="text-slate-300 text-[11px] leading-relaxed">
            The canonical validator successfully detected and rejected an incompatible legacy schema version with 100% certainty.
            The network fault root cause is marked <strong className="text-amber-300">INCONCLUSIVE</strong> ({confPercent}% diagnostic confidence) because non-compliant telemetry cannot support a confirmed network fault diagnosis.
          </p>
        </div>
      )}

      {/* Telemetry Conflict Explicitly Resolved Card (Fix 3) */}
      {conflict_status === 'RESOLVED' && resolved_conflict_details && (
        <div className="rounded-lg bg-emerald-950/20 border border-emerald-500/30 p-4 space-y-2.5">
          <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Multi-Agent Telemetry Conflict Resolution</span>
            </div>
            <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              CONFLICT RESOLVED (0.00 PENALTY)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-mono">
            <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
              <span className="text-amber-400 font-semibold block text-[10px] uppercase mb-0.5">Initial Hypothesis:</span>
              <span className="text-slate-200">{resolved_conflict_details.initial_hypothesis}</span>
            </div>
            <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
              <span className="text-emerald-400 font-semibold block text-[10px] uppercase mb-0.5">Final Selected Diagnosis:</span>
              <span className="text-slate-200">{resolved_conflict_details.selected_diagnosis}</span>
            </div>
          </div>

          <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300">
            <strong className="text-rose-400 font-semibold mr-1">Specific Refuting Evidence:</strong>
            {resolved_conflict_details.refuting_evidence}
          </div>

          <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300">
            <strong className="text-cyan-400 font-semibold mr-1">Why Selected:</strong>
            {resolved_conflict_details.resolution_reasoning}
          </div>
        </div>
      )}

      {/* Competing Root-Cause Hypotheses */}
      {alternative_causes.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-bold text-slate-200 uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <GitCompare className="w-4 h-4 text-amber-400" />
              Hypotheses Verification Matrix
            </span>
            <span className="text-slate-400 font-mono text-[11px] font-normal">
              {alternative_causes.length} Evaluated
            </span>
          </div>

          <div className="grid grid-cols-1 gap-2">
            {alternative_causes.slice(0, 3).map((hyp, index) => {
              const probPct = Math.round(hyp.probability * 100);
              const badge = getHypothesisBadge(hyp.status);
              const BadgeIcon = badge.icon;

              return (
                <div
                  key={hyp.hypothesis_id}
                  className={`p-3 rounded-lg border transition-all ${
                    hyp.status === 'CONFIRMED' || hyp.status === 'VALIDATED'
                      ? 'border-emerald-500/40 bg-emerald-950/15'
                      : hyp.status === 'REJECTED' || hyp.status === 'REFUTED'
                      ? 'border-rose-900/30 bg-rose-950/10 opacity-75'
                      : hyp.status === 'NOT EVALUATED' || hyp.status === 'NOT_EVALUATED' || hyp.status === 'UNKNOWN' || hyp.status === 'UNRESOLVED'
                      ? 'border-slate-800 bg-slate-900/40 text-slate-400'
                      : 'border-slate-800 bg-slate-950/60'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        #{index + 1}
                      </span>
                      <h4 className="text-xs font-bold text-slate-200">{hyp.name}</h4>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded border ${badge.bg}`}>
                        <BadgeIcon className="w-3 h-3" />
                        {badge.text}
                      </span>
                      <span className="text-[10px] font-mono font-bold text-slate-300 bg-slate-800 px-1.5 py-0.5 rounded">
                        {probPct}% Prob
                      </span>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 mb-1.5">{hyp.description}</p>

                  {hyp.reasoning && (
                    <div className="p-2 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-300">
                      <strong className="text-cyan-400 font-mono text-[10px] uppercase block mb-0.5">Rationale:</strong>
                      {hyp.reasoning}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Structured Investigation Explanation */}
      {investigation_explanation && (
        <div className="rounded-lg bg-slate-950 p-4 border border-slate-800 space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-bold text-cyan-300 uppercase tracking-wider">
              Autonomous Consensus Synthesis
            </span>
            <span className="text-[10px] font-mono text-slate-400">Multi-Agent Logic</span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            {investigation_explanation.final_resolution}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1 text-xs font-mono">
            {/* Supporting Empirical Evidence */}
            <div className="p-2.5 rounded bg-emerald-950/20 border border-emerald-500/20 space-y-1">
              <span className="text-emerald-400 font-semibold block text-[10px] uppercase">
                ✅ Corroborating Evidence:
              </span>
              <ul className="space-y-0.5 text-slate-300 list-disc list-inside text-[11px]">
                {investigation_explanation.supporting_evidence.slice(0, 3).map((s, idx) => (
                  <li key={idx} className="truncate">{s}</li>
                ))}
              </ul>
            </div>

            {/* Refuted Counter-Evidence */}
            <div className="p-2.5 rounded bg-rose-950/20 border border-rose-500/20 space-y-1">
              <span className="text-rose-400 font-semibold block text-[10px] uppercase">
                ❌ Disqualified Hypotheses:
              </span>
              <ul className="space-y-0.5 text-slate-300 list-disc list-inside text-[11px]">
                {investigation_explanation.refuting_evidence.slice(0, 3).map((r, idx) => (
                  <li key={idx} className="truncate">{r}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Actionable Remediation Runbooks */}
      {recommended_actions.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-bold text-slate-200 uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <Terminal className="w-4 h-4 text-emerald-400" />
              Actionable Remediation Runbook
            </span>
            <span className="text-slate-400 font-mono text-[11px] font-normal">
              {recommended_actions.length} Steps
            </span>
          </div>

          <div className="space-y-2">
            {recommended_actions.map((act) => {
              const isCopied = copiedStep === act.step;

              return (
                <div
                  key={act.step}
                  className="p-3 rounded-lg bg-slate-950 border border-slate-800 hover:border-slate-700 transition space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold flex items-center justify-center">
                        {act.step}
                      </span>
                      <h4 className="text-xs font-bold text-slate-200">{act.action}</h4>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-slate-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
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

                  <p className="text-xs text-slate-300 leading-relaxed">{act.rationale}</p>

                  {/* CLI Command Box */}
                  {act.command && (
                    <div className="relative group bg-slate-900 rounded p-2.5 border border-slate-800 font-mono text-xs">
                      <div className="flex items-center justify-between text-cyan-300 overflow-x-auto pr-8">
                        <code>$ {act.command}</code>
                      </div>
                      <button
                        onClick={() => copyCommand(act.command, act.step)}
                        className="absolute right-2 top-2 p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
                        title="Copy Command"
                      >
                        {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  )}

                  {act.rollback_plan && (
                    <div className="text-[11px] font-mono text-slate-400 bg-slate-900/40 p-2 rounded border border-slate-800/60">
                      <strong className="text-amber-400 font-semibold mr-1">Rollback Plan:</strong>
                      {act.rollback_plan}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Diagnostic Limitations & Missing Telemetry Notice */}
      {((limitations && limitations.length > 0) || (missing_telemetry && missing_telemetry.length > 0)) && (
        <div className="p-3.5 rounded-xl bg-purple-950/20 border border-purple-800/40 text-xs space-y-1.5">
          <div className="flex items-center gap-2 text-purple-300 font-bold">
            <Info className="w-4 h-4 text-purple-400" />
            <span>Diagnostic Limitations & Telemetry Caveats</span>
          </div>
          <ul className="list-disc list-inside text-slate-300 space-y-1 font-mono text-[11px]">
            {missing_telemetry.map((item, i) => (
              <li key={`miss-${i}`} className="text-amber-300">{item}</li>
            ))}
            {limitations.map((lim, i) => (
              <li key={`lim-${i}`}>{lim}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
