import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { motion } from 'framer-motion';
import { Server, Router, Network, Wifi, Database, AlertTriangle, ShieldCheck, Bot, Radio } from 'lucide-react';

// Custom device node component for React Flow
function DeviceNode({ data }) {
  const isImplicated = data.isImplicated;
  const isCommunicating = data.isCommunicating;
  const activeAgent = data.activeAgent;
  const status = data.status || 'UP';

  const getIcon = () => {
    switch (data.device_type) {
      case 'router':
        return <Router className="w-5 h-5 text-cyan-400" />;
      case 'switch':
        return <Network className="w-5 h-5 text-blue-400" />;
      case 'ap':
        return <Wifi className="w-5 h-5 text-violet-400" />;
      case 'server':
        return data.id?.includes('DB') ? (
          <Database className="w-5 h-5 text-emerald-400" />
        ) : (
          <Server className="w-5 h-5 text-amber-400" />
        );
      default:
        return <Network className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusBadge = () => {
    if (isImplicated) {
      return (
        <span className="flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40 animate-pulse">
          <AlertTriangle className="w-3 h-3" />
          FAULT
        </span>
      );
    }
    if (status === 'DEGRADED') {
      return (
        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/40">
          WARN
        </span>
      );
    }
    return (
      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
        OK
      </span>
    );
  };

  return (
    <div
      className={`relative px-4 py-3 rounded-xl bg-[#0f1422] border transition-all duration-300 min-w-[200px] shadow-xl cursor-pointer ${
        isCommunicating
          ? 'border-cyan-400 ring-2 ring-cyan-400/60 shadow-cyan-500/30'
          : isImplicated
          ? 'node-implicated-pulse border-rose-500 bg-rose-950/20'
          : 'border-[#1f293d] hover:border-cyan-500/60 hover:bg-[#131b2e]'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-cyan-500 !w-2.5 !h-2.5 !border-2 !border-black" />
      
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-[#182035] border border-[#23304c]">
            {getIcon()}
          </div>
          <div>
            <div className="text-xs font-bold text-white tracking-tight">{data.label}</div>
            <div className="text-[10px] font-mono text-slate-400">{data.ip}</div>
          </div>
        </div>
        {getStatusBadge()}
      </div>

      {/* Active Inter-Agent Communication Callout */}
      {isCommunicating && activeAgent && (
        <div className="mb-1.5 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/60 text-[10px] font-mono text-cyan-300 flex items-center gap-1 animate-pulse">
          <Bot className="w-3 h-3 text-cyan-400" />
          <span>{activeAgent} querying...</span>
        </div>
      )}

      <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between border-t border-[#1e2a40] pt-1.5 mt-1">
        <span>{data.role}</span>
        {isImplicated ? (
          <span className="text-rose-400 font-bold animate-pulse text-[9px] uppercase">
            Root Cause Target
          </span>
        ) : (
          <span className="text-slate-500 text-[9px]">Click for Telemetry</span>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-cyan-500 !w-2.5 !h-2.5 !border-2 !border-black" />
    </div>
  );
}

const nodeTypes = {
  router: DeviceNode,
  switch: DeviceNode,
  ap: DeviceNode,
  server: DeviceNode,
};

export default function NetworkTopology({
  topology,
  affectedDevices = [],
  faultPropagationPaths = [],
  activeCommunicatingNode = null,
  activeAgentId = null,
  onSelectDevice,
}) {
  const nodes = useMemo(() => {
    if (!topology || !topology.nodes) return [];
    return topology.nodes.map((node) => {
      const isImplicated = affectedDevices.includes(node.id);
      const isCommunicating = activeCommunicatingNode === node.id;
      return {
        ...node,
        data: {
          ...node.data,
          id: node.id,
          isImplicated,
          isCommunicating,
          activeAgent: isCommunicating ? activeAgentId : null,
          status: isImplicated ? 'CRITICAL' : 'UP',
        },
      };
    });
  }, [topology, affectedDevices, activeCommunicatingNode, activeAgentId]);

  // Compute edges with fault propagation path styling
  const edges = useMemo(() => {
    if (!topology || !topology.edges) return [];

    // Flatten propagation paths pairs: e.g. [["Core", "Agg"], ["Agg", "Edge"]]
    const propagationPairs = new Set();
    if (faultPropagationPaths && faultPropagationPaths.length > 0) {
      faultPropagationPaths.forEach((path) => {
        for (let i = 0; i < path.length - 1; i++) {
          propagationPairs.add(`${path[i]}->${path[i+1]}`);
          propagationPairs.add(`${path[i+1]}->${path[i]}`);
        }
      });
    }

    return topology.edges.map((edge) => {
      const sourceImplicated = affectedDevices.includes(edge.source);
      const targetImplicated = affectedDevices.includes(edge.target);
      const isPropagationEdge = propagationPairs.has(`${edge.source}->${edge.target}`) || propagationPairs.has(`${edge.target}->${edge.source}`);
      const isImplicatedPath = sourceImplicated || targetImplicated || isPropagationEdge;

      return {
        ...edge,
        animated: edge.animated || isImplicatedPath,
        label: isPropagationEdge ? '⚡ Fault Path' : edge.label,
        labelStyle: isPropagationEdge ? { fill: '#fb7185', fontWeight: 700, fontSize: 10 } : { fill: '#64748b', fontSize: 10 },
        labelBgStyle: isPropagationEdge ? { fill: '#4c0519', fillOpacity: 0.8 } : undefined,
        style: {
          stroke: isPropagationEdge ? '#f43f5e' : isImplicatedPath ? '#f43f5e' : '#38bdf8',
          strokeWidth: isPropagationEdge ? 3.0 : isImplicatedPath ? 2.2 : 1.5,
          strokeDasharray: isImplicatedPath ? '5 5' : undefined,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isPropagationEdge ? '#f43f5e' : isImplicatedPath ? '#f43f5e' : '#38bdf8',
        },
      };
    });
  }, [topology, affectedDevices, faultPropagationPaths]);

  return (
    <div className="w-full h-[420px] rounded-2xl bg-[#0b0e18] border border-[#1f293d] overflow-hidden relative shadow-2xl">
      {/* Topology Header overlay */}
      <div className="absolute top-3 left-4 z-10 flex flex-wrap items-center gap-2.5 bg-[#0f1422]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#1f293d]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
          <span className="text-xs font-semibold text-slate-200">Interactive Topology</span>
        </div>
        <span className="text-[11px] text-slate-400 font-mono">
          ({nodes.length} Nodes, {edges.length} Links)
        </span>
        {affectedDevices.length > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-rose-400 font-bold bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping"></span>
            <span>{affectedDevices.length} Implicated Node(s)</span>
          </div>
        )}
        {faultPropagationPaths.length > 0 && (
          <div className="flex items-center gap-1 text-[11px] font-mono text-amber-300 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/40">
            <span>⚡ Propagation Path Active</span>
          </div>
        )}
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(evt, node) => onSelectDevice && onSelectDevice(node)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.5}
        attributionPosition="bottom-right"
      >
        <Background color="#172033" gap={18} size={1} />
        <Controls className="!bg-[#111726] !border-[#1f293d]" />
        <MiniMap
          nodeColor={(n) => (affectedDevices.includes(n.id) ? '#f43f5e' : '#0284c7')}
          maskColor="rgba(7, 9, 14, 0.75)"
          className="!bg-[#0c101b] !border !border-[#1f293d] !rounded-lg"
        />
      </ReactFlow>
    </div>
  );
}
