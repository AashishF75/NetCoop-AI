import React from 'react';
import { Bot, Cpu, Radio, Network, FileCheck2, CheckCircle2, Clock, Loader2, ArrowRightLeft } from 'lucide-react';

const AGENT_META = {
  'perf-agent-01': {
    name: 'Performance Agent',
    role: 'Latency, Jitter, Packet Loss & Queue Drops',
    icon: Network,
    accentColor: 'text-cyan-400',
    indicatorColor: 'bg-cyan-400',
    accentBorder: 'border-cyan-500/40',
  },
  'infra-agent-01': {
    name: 'Infrastructure Health Agent',
    role: 'Host CPU, Memory, Discards & CRC Errors',
    icon: Cpu,
    accentColor: 'text-violet-400',
    indicatorColor: 'bg-violet-400',
    accentBorder: 'border-violet-500/40',
  },
  'conn-agent-01': {
    name: 'Connectivity Analysis Agent',
    role: 'Wireless RF (RSSI/SNR), DNS & DHCP',
    icon: Radio,
    accentColor: 'text-emerald-400',
    indicatorColor: 'bg-emerald-400',
    accentBorder: 'border-emerald-500/40',
  },
  'corr-agent-01': {
    name: 'Fault Correlation Agent',
    role: 'Inter-Agent Synthesis & Cross-Examination',
    icon: ArrowRightLeft,
    accentColor: 'text-amber-400',
    indicatorColor: 'bg-amber-400',
    accentBorder: 'border-amber-500/40',
  },
  'recom-agent-01': {
    name: 'Recommendation & Reporting Agent',
    role: 'Remediation Runbooks & Canonical Report',
    icon: FileCheck2,
    accentColor: 'text-sky-400',
    indicatorColor: 'bg-sky-400',
    accentBorder: 'border-sky-500/40',
  },
};

export default function AgentActivityPanel({ agentStates = [], activeAgentId, isDiagnosing }) {
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
          <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
            <Loader2 className="w-3 h-3 animate-spin text-cyan-400" />
            ANALYZING
          </span>
        );
      case 'COMPLETE':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            RESOLVED
          </span>
        );
      case 'AWAITING_PEER':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <Clock className="w-3 h-3 text-amber-400" />
            CROSS-EXAMINING
          </span>
        );
      default:
        return (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/80">
            IDLE
          </span>
        );
    }
  };

  return (
    <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 shadow-md">
      <div className="flex items-center justify-between gap-2 mb-3.5 border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-slate-100 tracking-wide">Multi-Agent Swarm Status</h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          5 Autonomous Diagnostic Agents
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
        {displayAgents.map((agent) => {
          const meta = AGENT_META[agent.agent_id] || {
            name: agent.name || agent.agent_id,
            role: agent.role || 'Domain Analysis Agent',
            icon: Bot,
            accentColor: 'text-cyan-400',
            indicatorColor: 'bg-cyan-400',
            accentBorder: 'border-cyan-500/40',
          };
          const AgentIcon = meta.icon;
          const isActive = activeAgentId === agent.agent_id;

          return (
            <div
              key={agent.agent_id}
              className={`rounded-lg p-3.5 transition-all border flex flex-col justify-between ${
                isActive
                  ? 'bg-slate-800/90 border-cyan-500/80 ring-1 ring-cyan-500/30 shadow-md shadow-cyan-950/40'
                  : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-slate-900 border border-slate-800">
                      <AgentIcon className={`w-4 h-4 ${meta.accentColor}`} />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-200 leading-tight">
                        {meta.name}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {agent.agent_id}
                      </div>
                    </div>
                  </div>
                  {getStatusBadge(agent.status)}
                </div>

                <p className="text-[11px] text-slate-400 mb-2 leading-relaxed">
                  {meta.role}
                </p>

                <div className="bg-slate-900/90 rounded p-2 border border-slate-800/80 mb-2">
                  <div className="text-[10px] uppercase font-mono text-slate-500 mb-0.5">Current Action</div>
                  <div className="text-xs text-slate-300 font-mono truncate" title={agent.current_task}>
                    {agent.current_task || 'Awaiting telemetry...'}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800/80">
                <span>Sent: <strong className="text-slate-200">{agent.messages_sent || 0}</strong></span>
                <span>Recv: <strong className="text-slate-200">{agent.messages_received || 0}</strong></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
