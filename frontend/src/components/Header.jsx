import React from 'react';
import { motion } from 'framer-motion';
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
  const getStatusColor = () => {
    switch (status) {
      case 'CONFIRMED': return 'bg-rose-500/20 text-rose-400 border-rose-500/40';
      case 'SUSPECTED': return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'INCONCLUSIVE': return 'bg-purple-500/20 text-purple-400 border-purple-500/40';
      case 'HEALTHY': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      default: return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40';
    }
  };

  return (
    <header className="border-b border-[#1f293d] bg-[#0c101b]/90 backdrop-blur-md sticky top-0 z-40 px-6 py-3.5">
      <div className="max-w-[1700px] mx-auto flex flex-wrap items-center justify-between gap-4">
        
        {/* Title & Brand */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 border border-cyan-400/30">
              <Activity className="w-5 h-5 text-white animate-pulse" />
            </div>
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                NetCoop <span className="text-cyan-400 font-extrabold">AI</span>
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider bg-cyan-950/70 border border-cyan-800/60 text-cyan-300">
                IIT-BBS Grand Finale
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Multi-Agent Network Fault Diagnosis & Canonical Protocol Interoperability
            </p>
          </div>
        </div>

        {/* Live System Badges */}
        <div className="hidden lg:flex items-center gap-3 text-xs font-mono">
          {telemetryOrigin === 'LIVE_DEVICE' ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-bold shadow-sm shadow-emerald-900/30">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>LIVE DEVICE</span>
            </div>
          ) : telemetryOrigin === 'LIVE_HOST' || telemetryOrigin === 'LIVE' ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-teal-500/20 text-teal-300 border border-teal-500/40 text-xs font-bold">
              <span className="w-2 h-2 rounded-full bg-teal-400"></span>
              <span>LIVE HOST PROBE</span>
            </div>
          ) : telemetryOrigin === 'CUSTOM_IMPORT' ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-bold">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              <span>CUSTOM IMPORT</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/40 text-xs font-bold">
              <span className="w-2 h-2 rounded-full bg-purple-400"></span>
              <span>SIMULATED SCENARIO</span>
            </div>
          )}

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#111726] border border-[#1f293d]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span className="text-slate-400">Protocol:</span>
            <span className="text-cyan-300 font-bold">Canonical v1.0.0</span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#111726] border border-[#1f293d]">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">Active Agents:</span>
            <span className="text-slate-200 font-bold">5 Autonomous</span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#111726] border border-[#1f293d]">
            <span className="text-slate-400">Incident:</span>
            <span className="text-amber-300 font-bold">{incidentId || 'INC-IDLE'}</span>
          </div>

          {status && (
            <div className={`px-3 py-1.5 rounded-lg border font-bold uppercase tracking-wider ${getStatusColor()}`}>
              {status}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2.5">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onOpenProtocolTester}
            className="flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg bg-[#141b2d] border border-[#1f293d] hover:border-cyan-500/50 hover:bg-[#1a233a] text-slate-200 transition-colors"
          >
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span className="hidden sm:inline">Protocol Inspector</span>
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onOpenReport}
            className="flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg bg-[#141b2d] border border-[#1f293d] hover:border-cyan-500/50 hover:bg-[#1a233a] text-slate-200 transition-colors"
          >
            <FileJson className="w-4 h-4 text-emerald-400" />
            <span className="hidden sm:inline">JSON Report</span>
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            disabled={isDiagnosing}
            onClick={onRunDiagnosis}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg transition-all shadow-lg ${
              isDiagnosing
                ? 'bg-cyan-600/50 text-cyan-200 cursor-not-allowed border border-cyan-500/40'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black shadow-cyan-500/25 border border-cyan-300/40 cursor-pointer'
            }`}
          >
            {isDiagnosing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-cyan-200" />
                <span>Agents Diagnosing...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-black" />
                <span>Run Multi-Agent Diagnosis</span>
              </>
            )}
          </motion.button>
        </div>

      </div>
    </header>
  );
}
