import React, { useState } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  Zap,
  Bot,
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

  const getPhaseBadge = (phase) => {
    switch (phase) {
      case 'INGESTION':
        return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
      case 'DOMAIN_ANALYSIS':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      case 'CROSS_EXAMINATION':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
      case 'CONFLICT_RESOLUTION':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'SYNTHESIS':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'REPORTING':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getEventTypeBadge = (eventType) => {
    switch (eventType) {
      case 'INCIDENT_DETECTED':
        return 'bg-blue-950/60 text-blue-300 border-blue-800/80';
      case 'AGENT_ACTIVATED':
        return 'bg-cyan-950/60 text-cyan-300 border-cyan-800/80';
      case 'EVIDENCE_COLLECTED':
        return 'bg-indigo-950/60 text-indigo-300 border-indigo-800/80';
      case 'CROSS_AGENT_QUERY':
        return 'bg-purple-950/60 text-purple-300 border-purple-800/80';
      case 'CROSS_AGENT_RESPONSE':
        return 'bg-violet-950/60 text-violet-300 border-violet-800/80';
      case 'CONFLICT_DETECTED':
        return 'bg-amber-950/80 text-amber-300 border-amber-600/80 font-semibold';
      case 'HYPOTHESIS_CONFIRMED':
      case 'ROOT_CAUSE_RESOLVED':
        return 'bg-emerald-950/70 text-emerald-300 border-emerald-600/80 font-semibold';
      default:
        return 'bg-slate-900 text-slate-300 border-slate-800';
    }
  };

  const handleStepPrev = () => {
    if (currentStepIndex > 0) onStepChange(currentStepIndex - 1);
  };

  const handleStepNext = () => {
    if (currentStepIndex < totalSteps - 1) onStepChange(currentStepIndex + 1);
  };

  const handleReset = () => {
    onStepChange(0);
  };

  if (totalSteps === 0) return null;

  return (
    <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 shadow-md">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3 border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
            <Zap className="w-4 h-4 fill-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-slate-100 tracking-wide">
                Autonomous Investigation Replay
              </h2>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-300">
                Step-by-Step Multi-Agent Playback
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Trace inter-agent negotiation, evidence verification, and consensus synthesis
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
              className="bg-slate-950 border border-slate-800 text-slate-200 rounded-lg px-2.5 py-1 text-xs outline-none cursor-pointer max-w-[220px] truncate"
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
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center mb-3 bg-slate-950/80 p-3 rounded-lg border border-slate-800/80">
        
        {/* Playback Buttons */}
        <div className="lg:col-span-5 flex items-center gap-2">
          <button
            onClick={handleReset}
            className="p-1.5 rounded-md bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition"
            title="Reset to Event 1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleStepPrev}
            disabled={currentStepIndex === 0}
            className="p-1.5 rounded-md bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 disabled:opacity-40 transition"
            title="Step Backward"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onTogglePlay}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md font-bold text-xs transition shadow-sm ${
              isPlaying
                ? 'bg-amber-500 hover:bg-amber-400 text-slate-950'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white'
            }`}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5 fill-current" />
                <span>Pause</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Play Replay</span>
              </>
            )}
          </button>

          <button
            onClick={handleStepNext}
            disabled={currentStepIndex === totalSteps - 1}
            className="p-1.5 rounded-md bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 disabled:opacity-40 transition"
            title="Step Forward"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>

          {/* Speed Selector */}
          <div className="flex items-center gap-1 bg-slate-900 p-0.5 rounded-md border border-slate-800 text-xs font-mono ml-2">
            {[1, 2, 3].map((s) => (
              <button
                key={s}
                onClick={() => onSpeedChange(s)}
                className={`px-2 py-0.5 rounded text-[11px] ${
                  speed === s ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* Timeline Scrubber */}
        <div className="lg:col-span-7 flex items-center gap-3">
          <span className="text-xs font-mono text-cyan-300 font-bold whitespace-nowrap min-w-[70px]">
            Step {currentStepIndex + 1}/{totalSteps}
          </span>

          <div className="flex-1 relative flex items-center">
            <input
              type="range"
              min={0}
              max={totalSteps - 1}
              value={currentStepIndex}
              onChange={(e) => onStepChange(parseInt(e.target.value, 10))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 focus:outline-none"
            />
          </div>

          <span className="text-xs font-mono text-slate-400 whitespace-nowrap min-w-[65px] text-right">
            +{currentEvent?.elapsed_ms || 0}ms
          </span>
        </div>
      </div>

      {/* Active Event Card */}
      {currentEvent && (() => {
        const eventPayload = currentEvent.agent_message || currentEvent.payload || currentEvent.evidence_snapshot;
        return (
          <div className="rounded-lg bg-slate-950/90 border border-slate-800 p-3.5 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border uppercase tracking-wider ${getPhaseBadge(currentEvent.phase)}`}>
                  {currentEvent.phase}
                </span>

                <span className={`px-2 py-0.5 rounded text-[11px] font-mono border ${getEventTypeBadge(currentEvent.event_type)}`}>
                  {currentEvent.event_type}
                </span>

                {/* Agent Badge */}
                <div className="flex items-center gap-1.5 text-xs font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                  <Bot className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-slate-300">{currentEvent.agent_id}</span>
                </div>

                {currentEvent.device_id && (
                  <span className="text-[11px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                    Target: <strong className="text-slate-200">{currentEvent.device_id}</strong>
                  </span>
                )}
              </div>

              {/* Toggle Payload */}
              {eventPayload && Object.keys(eventPayload).length > 0 && (
                <button
                  onClick={() => setShowPayload(!showPayload)}
                  className="flex items-center gap-1 text-[11px] font-mono text-slate-400 hover:text-cyan-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800 transition cursor-pointer"
                >
                  <FileCode className="w-3 h-3" />
                  <span>{showPayload ? 'Hide Data' : 'View Payload'}</span>
                </button>
              )}
            </div>

            {currentEvent.title && (
              <h3 className="text-xs sm:text-sm font-bold text-white tracking-tight">
                {currentEvent.title}
              </h3>
            )}

            <div className="text-xs text-slate-200 font-mono bg-slate-900/60 p-2.5 rounded border border-slate-800/80 leading-relaxed">
              {currentEvent.description}
            </div>

            {showPayload && eventPayload && (
              <div className="p-2 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono text-cyan-200/90 max-h-48 overflow-y-auto">
                <pre className="whitespace-pre-wrap">{JSON.stringify(eventPayload, null, 2)}</pre>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
