import React from 'react';
import { Activity, ShieldCheck, Play, FileJson, Cpu, Layers, RefreshCw } from 'lucide-react';

export default function Header({
  status,
  incidentId,
  telemetryOrigin = 'SIMULATED',
  isDiagnosing,
  onRunDiagnosis,
  onOpenReport,
  onOpenProtocolTester,
}) {
  const getStatusBadge = () => {
    switch (status) {
      case 'CONFIRMED':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      case 'SUSPECTED':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'INCONCLUSIVE':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
      case 'HEALTHY':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      default:
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
    }
  };

  const getOriginBadge = () => {
    switch (telemetryOrigin) {
      case 'LIVE_DEVICE':
        return {
          bg: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
          dot: 'bg-emerald-400',
          label: 'LIVE_DEVICE',
        };
      case 'LIVE_HOST':
      case 'LIVE':
        return {
          bg: 'bg-teal-500/15 text-teal-300 border-teal-500/40',
          dot: 'bg-teal-400',
          label: 'LIVE_HOST',
        };
      case 'GENERATED_TEST':
        return {
          bg: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
          dot: 'bg-amber-400',
          label: 'BENCHMARK GEN',
        };
      case 'CUSTOM_IMPORT':
        return {
          bg: 'bg-blue-500/15 text-blue-300 border-blue-500/40',
          dot: 'bg-blue-400',
          label: 'CUSTOM IMPORT',
        };
      default:
        return {
          bg: 'bg-slate-800 text-slate-300 border-slate-700',
          dot: 'bg-slate-400',
          label: 'SIMULATED',
        };
    }
  };

  const origin = getOriginBadge();

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md sticky top-0 z-40 px-4 lg:px-6 py-2.5">
      <div className="max-w-[1750px] mx-auto flex items-center justify-between gap-4">
        
        {/* Brand & Identity */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-sm shadow-cyan-500/20">
            <Activity className="w-4 h-4 text-white" />
          </div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
              NetCoop <span className="text-cyan-400 font-extrabold">AI</span>
            </h1>
            <span className="hidden sm:inline-block text-[11px] px-2 py-0.5 rounded font-medium bg-slate-800/80 border border-slate-700 text-slate-300">
              IIT-BBS Grand Finale
            </span>
          </div>
        </div>

        {/* System & Telemetry Provenance Status */}
        <div className="flex items-center gap-2 sm:gap-3 text-xs font-mono">
          {/* Prominent Provenance Badge */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-bold tracking-wide ${origin.bg}`}>
            <span className={`w-2 h-2 rounded-full ${origin.dot} animate-pulse`}></span>
            <span>{origin.label}</span>
          </div>

          {/* Incident Callout */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300">
            <span className="text-slate-500">INC:</span>
            <span className="font-semibold text-slate-200">{incidentId || 'IDLE'}</span>
          </div>

          {/* Diagnosis Status */}
          {status && (
            <div className={`hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-semibold ${getStatusBadge()}`}>
              <span>{status}</span>
            </div>
          )}

          {/* Active Agents Badge */}
          <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-400">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-300 font-medium">5 Agents Active</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {onOpenProtocolTester && (
            <button
              onClick={onOpenProtocolTester}
              title="Validate Canonical Schema"
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium transition"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
              <span>Protocol</span>
            </button>
          )}

          {onOpenReport && (
            <button
              onClick={onOpenReport}
              title="View Canonical JSON Report"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-medium transition"
            >
              <FileJson className="w-3.5 h-3.5 text-slate-400" />
              <span className="hidden sm:inline">Report JSON</span>
            </button>
          )}

          <button
            onClick={onRunDiagnosis}
            disabled={isDiagnosing}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition shadow-sm ${
              isDiagnosing
                ? 'bg-cyan-700 text-white cursor-wait opacity-80'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-900/30'
            }`}
          >
            {isDiagnosing ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Diagnosing...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Diagnosis</span>
              </>
            )}
          </button>
        </div>

      </div>
    </header>
  );
}
