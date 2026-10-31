import React, { useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { Activity, Gauge, Cpu, Radio, Zap } from 'lucide-react';

export default function TelemetryCharts({ telemetry = [] }) {
  const [activeTab, setActiveTab] = useState('performance'); // 'performance' | 'bandwidth' | 'infrastructure' | 'wireless'

  if (!telemetry || telemetry.length === 0) {
    return (
      <div className="w-full h-72 rounded-2xl bg-[#0f1422] border border-[#1f293d] flex items-center justify-center text-slate-500 font-mono text-xs">
        No telemetry loaded. Select a scenario or run diagnosis.
      </div>
    );
  }

  // Format data for chart display
  const chartData = telemetry.map((r) => ({
    name: r.device_id.replace('Switch', 'Sw').replace('Router', 'Rtr').replace('Server', 'Svr'),
    deviceId: r.device_id,
    latency: r.latency_ms ?? 0,
    jitter: r.jitter_ms ?? 0,
    packetLoss: r.packet_loss_pct ?? 0,
    utilization: r.utilization_pct ?? 0,
    throughput: r.throughput_mbps ?? 0,
    queueDrops: r.queue_drops_per_sec ?? 0,
    cpu: r.cpu_utilization_pct ?? 0,
    memory: r.memory_utilization_pct ?? 0,
    crcErrors: r.interface_crc_errors ?? 0,
    wifiRssi: r.wifi_rssi_dbm !== null && r.wifi_rssi_dbm !== undefined ? Math.abs(r.wifi_rssi_dbm) : 0,
    wifiRetries: r.wifi_retry_pct ?? 0,
    dnsLatency: r.dns_response_ms ?? 0,
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[#0b0f19] border border-[#22314d] p-2.5 rounded-lg shadow-xl text-xs font-mono">
          <div className="font-bold text-cyan-300 mb-1 border-b border-[#1f2c45] pb-1">{label}</div>
          {payload.map((entry, index) => (
            <div key={`item-${index}`} className="flex items-center justify-between gap-3 text-slate-300 py-0.5">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }}></span>
                <span>{entry.name}:</span>
              </span>
              <span className="font-bold text-white">
                {entry.value} {entry.unit || ''}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-4 shadow-xl">
      {/* Chart Navigation Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 border-b border-[#1f293d] pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white tracking-wide">Live Telemetry Ingestion Metrics</h2>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40 text-cyan-300">
            {telemetry.length} Devices Sampled
          </span>
        </div>

        <div className="flex items-center gap-1.5 bg-[#0a0d16] p-1 rounded-xl border border-[#1b2438] text-xs font-medium">
          <button
            onClick={() => setActiveTab('performance')}
            className={`px-3 py-1 rounded-lg transition-all ${
              activeTab === 'performance'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Latency & Jitter
          </button>
          <button
            onClick={() => setActiveTab('congestion')}
            className={`px-3 py-1 rounded-lg transition-all ${
              activeTab === 'congestion'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Queues & Drops
          </button>
          <button
            onClick={() => setActiveTab('infrastructure')}
            className={`px-3 py-1 rounded-lg transition-all ${
              activeTab === 'infrastructure'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            CPU & Hardware
          </button>
          <button
            onClick={() => setActiveTab('services')}
            className={`px-3 py-1 rounded-lg transition-all ${
              activeTab === 'services'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            RF & DNS
          </button>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          {activeTab === 'performance' && (
            <AreaChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="latencyGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.6} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="jitterGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2538" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis stroke="#64748b" tick={{ fontSize: 11 }} unit="ms" />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
              <Area type="monotone" dataKey="latency" name="Latency (ms)" stroke="#06b6d4" fillOpacity={1} fill="url(#latencyGrad)" strokeWidth={2} unit="ms" />
              <Area type="monotone" dataKey="jitter" name="Jitter (ms)" stroke="#f59e0b" fillOpacity={1} fill="url(#jitterGrad)" strokeWidth={2} unit="ms" />
            </AreaChart>
          )}

          {activeTab === 'congestion' && (
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2538" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" stroke="#64748b" tick={{ fontSize: 11 }} unit="pkts/s" />
              <YAxis yAxisId="right" orientation="right" stroke="#64748b" tick={{ fontSize: 11 }} unit="%" />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
              <Bar yAxisId="left" dataKey="queueDrops" name="Queue Drops" fill="#f43f5e" radius={[4, 4, 0, 0]} unit="pkts/s" />
              <Bar yAxisId="right" dataKey="utilization" name="Link Utilization" fill="#3b82f6" radius={[4, 4, 0, 0]} unit="%" />
              <Bar yAxisId="right" dataKey="packetLoss" name="Packet Loss" fill="#e11d48" radius={[4, 4, 0, 0]} unit="%" />
            </BarChart>
          )}

          {activeTab === 'infrastructure' && (
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2538" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
              <Line type="monotone" dataKey="cpu" name="CPU Load (%)" stroke="#a855f7" strokeWidth={2.5} dot={{ r: 4 }} unit="%" />
              <Line type="monotone" dataKey="memory" name="Memory (%)" stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} unit="%" />
              <Line type="monotone" dataKey="crcErrors" name="CRC Errors/s" stroke="#ef4444" strokeWidth={2.5} dot={{ r: 4 }} unit="err/s" />
            </LineChart>
          )}

          {activeTab === 'services' && (
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2538" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
              <Bar dataKey="dnsLatency" name="DNS Response" fill="#ec4899" radius={[4, 4, 0, 0]} unit="ms" />
              <Bar dataKey="wifiRetries" name="Wi-Fi Retries" fill="#f59e0b" radius={[4, 4, 0, 0]} unit="%" />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
