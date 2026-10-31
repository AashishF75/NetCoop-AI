import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquareCode,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  AlertCircle,
  HelpCircle,
  Zap,
  Filter,
} from 'lucide-react';

export default function InterAgentMessageLog({ messages = [] }) {
  const [filter, setFilter] = useState('ALL');
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);

  const getMessageTypeBadge = (type) => {
    switch (type) {
      case 'TELEMETRY_ANOMALY':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      case 'QUERY_EVIDENCE':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      case 'QUERY_RESPONSE':
        return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
      case 'CONFLICT_DETECTED':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse';
      case 'DIAGNOSTIC_SUMMARY':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
      case 'REMEDIATION_PLAN':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'SCHEMA_VERSION_MISMATCH':
        return 'bg-red-500/20 text-red-300 border-red-500/40';
      default:
        return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  const filteredMessages = messages.filter((m) => {
    if (filter === 'ALL') return true;
    if (filter === 'QUERIES') return m.message_type === 'QUERY_EVIDENCE' || m.message_type === 'QUERY_RESPONSE';
    if (filter === 'ANOMALIES') return m.message_type === 'TELEMETRY_ANOMALY';
    if (filter === 'CONFLICTS') return m.message_type === 'CONFLICT_DETECTED';
    if (filter === 'SYNTHESIS') return m.message_type === 'DIAGNOSTIC_SUMMARY' || m.message_type === 'REMEDIATION_PLAN';
    return true;
  });

  const handleCopy = (msg, idx) => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(JSON.stringify(msg, null, 2)).catch(() => {});
    }
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 1800);
  };

  return (
    <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-4 shadow-xl flex flex-col h-[520px]">
      {/* Header and Filter */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3 border-b border-[#1f293d] pb-3">
        <div className="flex items-center gap-2">
          <MessageSquareCode className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white tracking-wide">Canonical Inter-Agent Message Protocol Bus</h2>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40 text-cyan-300">
            {messages.length} Messages Exchanged
          </span>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-1 bg-[#0a0d16] p-1 rounded-xl border border-[#1b2438] text-[11px] font-medium">
          {['ALL', 'QUERIES', 'ANOMALIES', 'CONFLICTS', 'SYNTHESIS'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                filter === f
                  ? 'bg-cyan-500 text-black font-bold shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-2.5">
        {filteredMessages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-xs font-mono">
            No inter-agent messages matching current filter. Run a diagnosis scenario to populate protocol stream.
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {filteredMessages.map((msg, idx) => {
              const isExpanded = expandedIndex === idx;
              const isCopied = copiedIndex === idx;

              return (
                <motion.div
                  key={`${msg.agent_id}-${msg.timestamp}-${idx}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.25, delay: Math.min(idx * 0.03, 0.3) }}
                  className="rounded-xl bg-[#0a0d16] border border-[#1b253b] hover:border-cyan-500/40 p-3 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    {/* Routing */}
                    <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                      <span className="font-bold text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-900/60">
                        {msg.agent_id}
                      </span>
                      {msg.target_agent_id && (
                        <>
                          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                          <span className="font-bold text-blue-300 bg-blue-950/60 px-2 py-0.5 rounded border border-blue-900/60">
                            {msg.target_agent_id}
                          </span>
                        </>
                      )}
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getMessageTypeBadge(msg.message_type)}`}>
                        {msg.message_type}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        v{msg.schema_version}
                      </span>
                    </div>

                    {/* Metadata & Actions */}
                    <div className="flex items-center gap-2">
                      {msg.confidence > 0 && (
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-900/40">
                          {Math.round(msg.confidence * 100)}% Conf
                        </span>
                      )}
                      <button
                        onClick={() => handleCopy(msg, idx)}
                        className="p-1 text-slate-400 hover:text-white rounded hover:bg-[#162035]"
                        title="Copy JSON Payload"
                      >
                        {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                      <button
                        onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                        className="p-1 text-slate-400 hover:text-white rounded hover:bg-[#162035]"
                        title="Toggle JSON Payload View"
                      >
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  {/* Findings Summary */}
                  <div className="mt-2 text-xs text-slate-200 font-sans leading-relaxed">
                    {msg.findings && msg.findings.length > 0 ? (
                      msg.findings.map((f, i) => (
                        <p key={i} className="text-slate-200">
                          {f}
                        </p>
                      ))
                    ) : (
                      <p className="text-slate-400 italic">No textual findings attached</p>
                    )}
                  </div>

                  {/* Expandable JSON Schema Viewer */}
                  {isExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-2.5 pt-2 border-t border-[#1b253b]"
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400 mb-1">
                        <span>Canonical Pydantic AgentMessage Payload</span>
                        <span>UUID: {msg.correlation_id || 'N/A'}</span>
                      </div>
                      <pre className="bg-[#06080e] p-2.5 rounded-lg text-[10px] font-mono text-slate-300 overflow-x-auto border border-[#182133] max-h-48">
                        {JSON.stringify(msg, null, 2)}
                      </pre>
                    </motion.div>
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
