import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  Zap,
  ArrowRight,
  ShieldAlert,
  Bot,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Clock,
  Layers,
  ChevronDown,
  History,
  FileCode,
} from 'lucide-react';

export default function InvestigationReplay({
  timelineEvents = [],
  currentStepIndex = 0,
  onStepChange,
  isPlaying,
  onTogglePlay,
  speed = 1,
  onSpeedChange,
  pastInvestigations = [],
  onSelectPastInvestigation,
  activeIncidentId,
}) {
  const [showPayload, setShowPayload] = useState(false);

  const totalSteps = timelineEvents.length;
  const currentEvent = totalSteps > 0 ? timelineEvents[currentStepIndex] || timelineEvents[0] : null;

  const getPhaseColor = (phase) => {
    switch (phase) {
      case 'INGESTION': return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
      case 'DOMAIN_ANALYSIS': return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
      case 'CROSS_EXAMINATION': return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
      case 'CONFLICT_RESOLUTION': return 'bg-amber-500/25 text-amber-300 border-amber-500/50 animate-pulse';
      case 'SYNTHESIS': return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
      case 'REPORTING': return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      default: return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  const getEventTypeBadge = (eventType) => {
    switch (eventType) {
      case 'INCIDENT_DETECTED': return 'bg-blue-950/60 text-blue-300 border-blue-800';
      case 'AGENT_ACTIVATED': return 'bg-cyan-950/60 text-cyan-300 border-cyan-800';
      case 'EVIDENCE_COLLECTED': return 'bg-indigo-950/60 text-indigo-300 border-indigo-800';
      case 'CROSS_AGENT_QUERY': return 'bg-purple-950/60 text-purple-300 border-purple-800';
      case 'CROSS_AGENT_RESPONSE': return 'bg-violet-950/60 text-violet-300 border-violet-800';
      case 'CONFLICT_DETECTED': return 'bg-amber-950/80 text-amber-300 border-amber-600 font-bold';
      case 'HYPOTHESIS_CHALLENGED': return 'bg-rose-950/60 text-rose-300 border-rose-800';
      case 'HYPOTHESIS_CONFIRMED': return 'bg-emerald-950/60 text-emerald-300 border-emerald-800';
      case 'ROOT_CAUSE_RESOLVED': return 'bg-emerald-900/60 text-emerald-200 border-emerald-500 font-bold';
      case 'REMEDIATION_GENERATED': return 'bg-teal-950/60 text-teal-300 border-teal-800';
      case 'INVESTIGATION_COMPLETE': return 'bg-slate-800 text-slate-200 border-slate-600';
      default: return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const handleStepPrev = () => {
    if (currentStepIndex > 0) {
      onStepChange(currentStepIndex - 1);
    }
  };

  const handleStepNext = () => {
    if (currentStepIndex < totalSteps - 1) {
      onStepChange(currentStepIndex + 1);
    }
  };

  const handleReset = () => {
    onStepChange(0);
  };

  if (totalSteps === 0) {
    return null;
  }

  const progressPercent = totalSteps > 1 ? Math.round((currentStepIndex / (totalSteps - 1)) * 100) : 100;

  return (
    <div className="rounded-2xl bg-[#0c101c] border border-cyan-500/30 p-4 shadow-2xl relative overflow-hidden">
      {/* Glow highlight along the top edge */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-80"></div>

      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3 border-b border-[#1b253b] pb-2.5">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/40">
            <Zap className="w-4 h-4 fill-cyan-400 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white tracking-wide">
                Autonomous Investigation Replay
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800 text-cyan-300 font-semibold">
                Event-Driven Architecture
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Replay real-time multi-agent negotiation, cross-examination, conflict resolution & synthesis
            </p>
          </div>
        </div>

        {/* Past Investigation Replay Dropdown */}
        {pastInvestigations.length > 0 && (
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400 flex items-center gap-1">
              <History className="w-3.5 h-3.5 text-cyan-400" />
              Replay Session:
            </span>
            <select
              value={activeIncidentId || ''}
              onChange={(e) => onSelectPastInvestigation(e.target.value)}
              className="bg-[#090d16] border border-[#1f2c45] focus:border-cyan-500 text-slate-200 rounded-lg px-2.5 py-1 text-xs outline-none cursor-pointer max-w-[200px] truncate"
            >
              {pastInvestigations.map((inv) => (
                <option key={inv.incident_id} value={inv.incident_id}>
                  #{inv.incident_id} — {inv.status} ({inv.event_count || 0} evts)
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Replay Controls & Timeline Scrubber */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center mb-3.5 bg-[#080b14] p-3 rounded-xl border border-[#182338]">
        
        {/* Playback Buttons */}
        <div className="lg:col-span-4 flex items-center gap-2">
          <button
            onClick={handleReset}
            className="p-1.5 rounded-lg bg-[#141b2c] hover:bg-[#1d273f] text-slate-300 border border-[#212e47] transition-colors"
            title="Reset to Event 1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleStepPrev}
            disabled={currentStepIndex === 0}
            className="p-1.5 rounded-lg bg-[#141b2c] hover:bg-[#1d273f] text-slate-300 border border-[#212e47] disabled:opacity-40 transition-colors"
            title="Step Backward"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onTogglePlay}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg font-bold text-xs shadow-md transition-all ${
              isPlaying
                ? 'bg-amber-500 hover:bg-amber-400 text-black shadow-amber-500/20'
                : 'bg-cyan-500 hover:bg-cyan-400 text-black shadow-cyan-500/20'
            }`}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5 fill-black" />
                <span>Pause</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-black" />
                <span>Play Replay</span>
              </>
            )}
          </button>

          <button
            onClick={handleStepNext}
            disabled={currentStepIndex === totalSteps - 1}
            className="p-1.5 rounded-lg bg-[#141b2c] hover:bg-[#1d273f] text-slate-300 border border-[#212e47] disabled:opacity-40 transition-colors"
            title="Step Forward"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>

          {/* Speed Selector */}
          <div className="flex items-center gap-1 bg-[#101626] p-0.5 rounded-lg border border-[#1e2a42] text-[11px] font-mono ml-2">
            {[1, 2, 3].map((s) => (
              <button
                key={s}
                onClick={() => onSpeedChange(s)}
                className={`px-1.5 py-0.5 rounded ${
                  speed === s ? 'bg-cyan-500 text-black font-bold' : 'text-slate-400 hover:text-white'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* Timeline Scrubber */}
        <div className="lg:col-span-8 flex items-center gap-3">
          <span className="text-xs font-mono text-cyan-300 font-bold whitespace-nowrap min-w-[75px]">
            {currentStepIndex + 1} / {totalSteps}
          </span>

          <div className="flex-1 relative flex items-center">
            <input
              type="range"
              min={0}
              max={totalSteps - 1}
              value={currentStepIndex}
              onChange={(e) => onStepChange(parseInt(e.target.value, 10))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 focus:outline-none"
            />
          </div>

          <span className="text-[11px] font-mono text-slate-400 whitespace-nowrap min-w-[65px] text-right">
            {currentEvent?.elapsed_ms || 0} ms
          </span>
        </div>
      </div>

      {/* Active Event Card */}
      {currentEvent && (
        <motion.div
          key={currentEvent.event_id}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="rounded-xl bg-[#090d17] border border-[#1b263d] p-3.5"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wider ${getPhaseColor(currentEvent.phase)}`}>
                {currentEvent.phase}
              </span>

              <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${getEventTypeBadge(currentEvent.event_type)}`}>
                {currentEvent.event_type}
              </span>

              {/* Agent Badge */}
              <div className="flex items-center gap-1.5 text-xs font-mono bg-[#111726] px-2 py-0.5 rounded border border-[#1e2a42]">
                <Bot className="w-3.5 h-3.5 text-cyan-400" />
                <span className="text-cyan-300 font-bold">{currentEvent.agent_id}</span>
                {currentEvent.target_agent_id && (
                  <>
                    <ArrowRight className="w-3 h-3 text-slate-500" />
                    <span className="text-blue-300 font-bold">{currentEvent.target_agent_id}</span>
                  </>
                )}
              </div>

              {currentEvent.device_id && (
                <span className="text-xs font-mono text-slate-300 bg-[#162035] px-2 py-0.5 rounded border border-[#22314d]">
                  Target: <strong className="text-white">{currentEvent.device_id}</strong>
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {currentEvent.agent_message && (
                <button
                  onClick={() => setShowPayload(!showPayload)}
                  className="flex items-center gap-1 px-2 py-0.5 rounded bg-[#131b2e] hover:bg-[#1a253e] text-[10px] font-mono text-cyan-400 border border-[#1e2a42]"
                >
                  <FileCode className="w-3 h-3" />
                  <span>{showPayload ? 'Hide Payload' : 'Inspect JSON'}</span>
                </button>
              )}
              <span className="text-[10px] font-mono text-slate-500">
                T+{currentEvent.elapsed_ms}ms
              </span>
            </div>
          </div>

          <h3 className="text-xs sm:text-sm font-bold text-white mb-1 tracking-tight">
            {currentEvent.title}
          </h3>

          <p className="text-xs text-slate-300 font-sans leading-relaxed mb-2">
            {currentEvent.description}
          </p>

          {/* Evidence Snapshot (if present) */}
          {currentEvent.evidence_snapshot && Object.keys(currentEvent.evidence_snapshot).length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-[#162035] text-[11px] font-mono">
              <span className="text-slate-400 font-bold">Evidence Counters:</span>
              {Object.entries(currentEvent.evidence_snapshot).slice(0, 5).map(([k, v]) => (
                <span key={k} className="px-2 py-0.5 rounded bg-[#101728] border border-[#1d2942] text-slate-300">
                  {k}: <strong className="text-cyan-300">{String(v)}</strong>
                </span>
              ))}
            </div>
          )}

          {/* Inspectable Message Payload Drawer */}
          {showPayload && currentEvent.agent_message && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-2.5 pt-2 border-t border-[#182338]"
            >
              <div className="text-[10px] font-mono text-cyan-400 mb-1">
                Canonical AgentMessage Payload ({currentEvent.agent_message.schema_version || '1.0.0'})
              </div>
              <pre className="bg-[#05070d] p-2.5 rounded-lg text-[10px] font-mono text-emerald-300 overflow-x-auto border border-[#182338] max-h-40">
                {JSON.stringify(currentEvent.agent_message, null, 2)}
              </pre>
            </motion.div>
          )}
        </motion.div>
      )}
    </div>
  );
}

