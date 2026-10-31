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
import { Server, Router, Network, Wifi, Database, AlertTriangle, ShieldCheck } from 'lucide-react';

// Custom device node component for React Flow
function DeviceNode({ data }) {
  const isImplicated = data.isImplicated;
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
        <span className="flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40">
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
      className={`relative px-4 py-3 rounded-xl bg-[#0f1422] border transition-all duration-300 min-w-[190px] shadow-xl ${
        isImplicated
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

      <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between border-t border-[#1e2a40] pt-1.5 mt-1.5">
        <span>{data.role}</span>
        {isImplicated && (
          <span className="text-rose-400 font-bold animate-pulse text-[9px] uppercase">
            Root Cause Target
          </span>
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

export default function NetworkTopology({ topology, affectedDevices = [], onSelectDevice }) {
  const nodes = useMemo(() => {
    if (!topology || !topology.nodes) return [];
    return topology.nodes.map((node) => {
      const isImplicated = affectedDevices.includes(node.id);
      return {
        ...node,
        data: {
          ...node.data,
          id: node.id,
          isImplicated,
          status: isImplicated ? 'CRITICAL' : 'UP',
        },
      };
    });
  }, [topology, affectedDevices]);

  const edges = useMemo(() => {
    if (!topology || !topology.edges) return [];
    return topology.edges.map((edge) => {
      const sourceImplicated = affectedDevices.includes(edge.source);
      const targetImplicated = affectedDevices.includes(edge.target);
      const isImplicatedPath = sourceImplicated || targetImplicated;

      return {
        ...edge,
        animated: edge.animated || isImplicatedPath,
        style: {
          stroke: isImplicatedPath ? '#f43f5e' : '#38bdf8',
          strokeWidth: isImplicatedPath ? 2.5 : 1.5,
          strokeDasharray: isImplicatedPath ? '5 5' : undefined,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isImplicatedPath ? '#f43f5e' : '#38bdf8',
        },
      };
    });
  }, [topology, affectedDevices]);

  return (
    <div className="w-full h-[420px] rounded-2xl bg-[#0b0e18] border border-[#1f293d] overflow-hidden relative shadow-2xl">
      {/* Topology Header overlay */}
      <div className="absolute top-3 left-4 z-10 flex items-center gap-3 bg-[#0f1422]/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#1f293d]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
          <span className="text-xs font-semibold text-slate-200">Interactive Network Topology</span>
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
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
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
