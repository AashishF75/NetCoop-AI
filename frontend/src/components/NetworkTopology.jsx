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
        return <Router className="w-4 h-4 text-cyan-400" />;
      case 'switch':
        return <Network className="w-4 h-4 text-blue-400" />;
      case 'ap':
        return <Wifi className="w-4 h-4 text-violet-400" />;
      case 'server':
        return data.id?.includes('DB') ? (
          <Database className="w-4 h-4 text-emerald-400" />
        ) : (
          <Server className="w-4 h-4 text-amber-400" />
        );
      default:
        return <Network className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusBadge = () => {
    if (isImplicated) {
      return (
        <span className="flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/40">
          <AlertTriangle className="w-3 h-3 text-rose-400" />
          FAULT
        </span>
      );
    }
    if (status === 'DEGRADED') {
      return (
        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">
          WARN
        </span>
      );
    }
    return (
      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
        OK
      </span>
    );
  };

  return (
    <div
      className={`relative px-3.5 py-2.5 rounded-xl border transition-all duration-200 min-w-[195px] shadow-lg cursor-pointer ${
        isCommunicating
          ? 'bg-slate-900 border-cyan-400 ring-2 ring-cyan-500/40 shadow-cyan-900/40'
          : isImplicated
          ? 'bg-rose-950/30 border-rose-500 ring-1 ring-rose-500/50 shadow-rose-950/50'
          : 'bg-[#0e1422] border-slate-800 hover:border-slate-600 hover:bg-[#12192b]'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-cyan-500 !w-2 !h-2 !border !border-black" />
      
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60">
            {getIcon()}
          </div>
          <div>
            <div className="text-xs font-bold text-slate-100 tracking-tight">{data.label}</div>
            <div className="text-[10px] font-mono text-slate-400">{data.ip}</div>
          </div>
        </div>
        {getStatusBadge()}
      </div>

      {/* Active Inter-Agent Communication Callout */}
      {isCommunicating && activeAgent && (
        <div className="mb-1 px-1.5 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/40 text-[9px] font-mono text-cyan-300 flex items-center gap-1 animate-pulse">
          <Bot className="w-2.5 h-2.5 text-cyan-400" />
          <span>{activeAgent} querying...</span>
        </div>
      )}

      <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-1 mt-1">
        <span className="capitalize">{data.role}</span>
        {isImplicated ? (
          <span className="text-rose-400 font-bold text-[9px] uppercase tracking-wide">
            Root Target
          </span>
        ) : (
          <span className="text-slate-500 text-[9px]">Click for Details</span>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-cyan-500 !w-2 !h-2 !border !border-black" />
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
    <div className="w-full h-[420px] rounded-2xl bg-[#090d16] border border-slate-800/90 overflow-hidden relative shadow-xl">
      {/* Topology Header overlay */}
      <div className="absolute top-3 left-4 z-10 flex flex-wrap items-center gap-2.5 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700/70 shadow-md">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
          <span className="text-xs font-semibold text-slate-200">Interactive Topology</span>
        </div>
        <span className="text-[11px] text-slate-400 font-mono">
          ({nodes.length} Nodes, {edges.length} Links)
        </span>
        {affectedDevices.length > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-rose-300 font-semibold bg-rose-500/15 px-2 py-0.5 rounded border border-rose-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
            <span>{affectedDevices.length} Implicated Node(s)</span>
          </div>
        )}
        {faultPropagationPaths.length > 0 && (
          <div className="flex items-center gap-1 text-[11px] font-mono text-amber-300 bg-amber-950/50 px-2 py-0.5 rounded border border-amber-700/40">
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
        <Background color="#161f30" gap={18} size={1} />
        <Controls className="!bg-[#0f172a] !border-slate-800" />
        <MiniMap
          nodeColor={(n) => (affectedDevices.includes(n.id) ? '#f43f5e' : '#0284c7')}
          maskColor="rgba(7, 9, 14, 0.75)"
          className="!bg-[#0c101b] !border !border-slate-800 !rounded-lg"
        />
      </ReactFlow>
    </div>
  );
}
