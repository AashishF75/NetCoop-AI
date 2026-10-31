import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Cpu, Radio, Network, FileCheck2, CheckCircle2, Clock, Loader2, ArrowRightLeft } from 'lucide-react';

const AGENT_META = {
  'perf-agent-01': {
    name: 'Performance Agent',
    role: 'Latency, Jitter, Loss & Queue Drops',
    icon: Network,
    accent: 'cyan',
    border: 'border-cyan-500/40',
    bg: 'from-cyan-950/30 to-blue-950/20',
  },
  'infra-agent-01': {
    name: 'Infrastructure Health Agent',
    role: 'CPU, Memory, Transceivers & CRC Errors',
    icon: Cpu,
    accent: 'purple',
    border: 'border-purple-500/40',
    bg: 'from-purple-950/30 to-slate-950/20',
  },
  'conn-agent-01': {
    name: 'Connectivity Analysis Agent',
    role: 'Wireless RF (RSSI/SNR), DNS & DHCP',
    icon: Radio,
    accent: 'emerald',
    border: 'border-emerald-500/40',
    bg: 'from-emerald-950/30 to-slate-950/20',
  },
  'corr-agent-01': {
    name: 'Fault Correlation Agent',
    role: 'Inter-Agent Synthesis & Conflict Resolution',
    icon: ArrowRightLeft,
    accent: 'amber',
    border: 'border-amber-500/40',
    bg: 'from-amber-950/30 to-slate-950/20',
  },
  'recom-agent-01': {
    name: 'Recommendation & Reporting Agent',
    role: 'Remediation Runbooks & Canonical Report',
    icon: FileCheck2,
    accent: 'rose',
    border: 'border-rose-500/40',
    bg: 'from-rose-950/30 to-slate-950/20',
  },
};

export default function AgentActivityPanel({ agentStates = [], activeAgentId, isDiagnosing }) {
  // Fallback defaults if no diagnosis run yet
  const defaultAgents = [
    { agent_id: 'perf-agent-01', status: 'IDLE', current_task: 'Standing by for telemetry ingestion', messages_sent: 0, messages_received: 0 },
    { agent_id: 'infra-agent-01', status: 'IDLE', current_task: 'Standing by for telemetry ingestion', messages_sent: 0, messages_received: 0 },
    { agent_id: 'conn-agent-01', status: 'IDLE', current_task: 'Standing by for telemetry ingestion', messages_sent: 0, messages_received: 0 },
    { agent_id: 'corr-agent-01', status: 'IDLE', current_task: 'Standing by for peer findings', messages_sent: 0, messages_received: 0 },
    { agent_id: 'recom-agent-01', status: 'IDLE', current_task: 'Standing by for correlation report', messages_sent: 0, messages_received: 0 },
  ];

  const displayAgents = agentStates.length > 0 ? agentStates : defaultAgents;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ANALYZING':
        return (
          <span className="flex items-center gap-1.5 text-[11px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin text-cyan-400" />
            ANALYZING
          </span>
        );
      case 'COMPLETE':
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            RESOLVED
          </span>
        );
      case 'AWAITING_PEER':
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
            <Clock className="w-3 h-3 text-amber-400" />
            CROSS-EXAMINING
          </span>
        );
      default:
        return (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
            IDLE
          </span>
        );
    }
  };

  return (
    <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-4 shadow-xl">
      <div className="flex items-center justify-between gap-2 mb-3.5 border-b border-[#1f293d] pb-2.5">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white tracking-wide">Multi-Agent Swarm Status</h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          5 Agents Coordinated
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
        {displayAgents.map((agent, index) => {
          const meta = AGENT_META[agent.agent_id] || {
            name: agent.name || agent.agent_id,
            role: agent.role || 'Autonomous Network Agent',
            icon: Bot,
            border: 'border-slate-700',
            bg: 'from-slate-900 to-slate-950',
          };
          const Icon = meta.icon;
          const isAnalyzing = agent.status === 'ANALYZING';
          const isComplete = agent.status === 'COMPLETE';

          return (
            <motion.div
              key={agent.agent_id}
              initial={{ opacity: 0, y: 15 }}
              animate={{
                opacity: 1,
                y: 0,
                scale: isAnalyzing ? [1, 1.02, 1] : 1,
              }}
              transition={{
                duration: 0.35,
                delay: index * 0.08,
                repeat: isAnalyzing ? Infinity : 0,
                repeatType: 'reverse',
                repeatDelay: 1.2,
              }}
              whileHover={{ y: -3, transition: { duration: 0.2 } }}
              className={`relative rounded-xl p-3.5 bg-gradient-to-b ${meta.bg} border ${
                isAnalyzing ? 'border-cyan-400 shadow-lg shadow-cyan-500/20' : meta.border
              } transition-all flex flex-col justify-between`}
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="p-1.5 rounded-lg bg-[#141b2b] border border-[#232f48]">
                    <Icon className="w-4 h-4 text-slate-200" />
                  </div>
                  {getStatusBadge(agent.status)}
                </div>

                <h3 className="text-xs font-bold text-white tracking-tight">{meta.name}</h3>
                <p className="text-[10px] text-slate-400 mb-2 leading-tight">{meta.role}</p>

                <div className="text-[11px] font-mono text-slate-300 bg-[#0a0d17]/80 rounded-lg p-2 border border-[#1b253b] mb-3 min-h-[46px] flex items-center">
                  <p className="line-clamp-2">{agent.current_task || 'Idle'}</p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-[#1b253b] text-[10px] font-mono text-slate-400">
                <span>Sent: <strong className="text-white">{agent.messages_sent || 0}</strong></span>
                <span>Recv: <strong className="text-white">{agent.messages_received || 0}</strong></span>
                <span className="text-cyan-400">v1.0.0</span>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
