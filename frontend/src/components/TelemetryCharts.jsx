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
import { Activity, Gauge, Cpu, Radio, Zap, AlertTriangle, ShieldCheck, CheckCircle2, HelpCircle } from 'lucide-react';

export default function TelemetryCharts({ telemetry = [], telemetryOrigin, canonicalReport }) {
  const [activeTab, setActiveTab] = useState('performance'); // 'performance' | 'congestion' | 'infrastructure' | 'services'

  if (!telemetry || telemetry.length === 0) {
    return (
      <div className="w-full h-72 rounded-2xl bg-[#0f1422] border border-[#1f293d] flex items-center justify-center text-slate-500 font-mono text-xs">
        No telemetry loaded. Select a scenario or run diagnosis.
      </div>
    );
  }

  // Detect dominant telemetry provenance across sampled records
  const detectedOrigin =
    telemetryOrigin ||
    telemetry[0]?.telemetry_origin ||
    canonicalReport?.telemetry_origin ||
    'SIMULATED_SCENARIO';

  const getOriginBadge = (orig) => {
    switch (orig) {
      case 'LIVE_DEVICE':
        return {
          label: '🟢 LIVE_DEVICE (Target Probe)',
          shortLabel: 'LIVE_DEVICE',
          badgeClass: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
          isLive: true,
        };
      case 'LIVE_HOST':
        return {
          label: '🟢 LIVE_HOST (Host Kernel)',
          shortLabel: 'LIVE_HOST',
          badgeClass: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
          isLive: true,
        };
      case 'CUSTOM_IMPORT':
        return {
          label: '🔵 CUSTOM_IMPORT (CSV / JSON)',
          shortLabel: 'CUSTOM_IMPORT',
          badgeClass: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
          isLive: false,
        };
      case 'GENERATED_TEST':
        return {
          label: '🟡 GENERATED_TEST (Synthetic Benchmark)',
          shortLabel: 'GENERATED_TEST',
          badgeClass: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
          isLive: false,
        };
      default:
        return {
          label: '🟣 SIMULATED_SCENARIO (Benchmark Digital Twin)',
          shortLabel: 'SIMULATED_SCENARIO',
          badgeClass: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
          isLive: false,
        };
    }
  };

  const originBadge = getOriginBadge(detectedOrigin);

  // Format data for chart display — NEVER replace null/undefined with 0!
  const chartData = telemetry.map((r) => {
    const devOrigin = r.telemetry_origin || detectedOrigin;
    return {
      name: r.device_id.replace('Switch', 'Sw').replace('Router', 'Rtr').replace('Server', 'Svr'),
      deviceId: r.device_id,
      origin: devOrigin,
      isLive: devOrigin === 'LIVE_DEVICE' || devOrigin === 'LIVE_HOST',
      latency: r.latency_ms !== null && r.latency_ms !== undefined ? Number(r.latency_ms) : null,
      jitter: r.jitter_ms !== null && r.jitter_ms !== undefined ? Number(r.jitter_ms) : null,
      packetLoss: r.packet_loss_pct !== null && r.packet_loss_pct !== undefined ? Number(r.packet_loss_pct) : null,
      utilization: r.utilization_pct !== null && r.utilization_pct !== undefined ? Number(r.utilization_pct) : null,
      throughput: r.throughput_mbps !== null && r.throughput_mbps !== undefined ? Number(r.throughput_mbps) : null,
      queueDrops: r.queue_drops_per_sec !== null && r.queue_drops_per_sec !== undefined ? Number(r.queue_drops_per_sec) : null,
      cpu: r.cpu_utilization_pct !== null && r.cpu_utilization_pct !== undefined ? Number(r.cpu_utilization_pct) : null,
      memory: r.memory_utilization_pct !== null && r.memory_utilization_pct !== undefined ? Number(r.memory_utilization_pct) : null,
      crcErrors: r.interface_crc_errors !== null && r.interface_crc_errors !== undefined ? Number(r.interface_crc_errors) : null,
      wifiRssi: r.wifi_rssi_dbm !== null && r.wifi_rssi_dbm !== undefined ? Math.abs(Number(r.wifi_rssi_dbm)) : null,
      wifiRetries: r.wifi_retry_pct !== null && r.wifi_retry_pct !== undefined ? Number(r.wifi_retry_pct) : null,
      dnsLatency: r.dns_response_ms !== null && r.dns_response_ms !== undefined ? Number(r.dns_response_ms) : null,
    };
  });

  // Metric presence indicators across dataset
  const hasLatency = chartData.some((d) => d.latency !== null);
  const hasJitter = chartData.some((d) => d.jitter !== null);
  const hasPacketLoss = chartData.some((d) => d.packetLoss !== null);
  const hasQueueDrops = chartData.some((d) => d.queueDrops !== null);
  const hasUtilization = chartData.some((d) => d.utilization !== null);
  const hasCpu = chartData.some((d) => d.cpu !== null);
  const hasMemory = chartData.some((d) => d.memory !== null);
  const hasCrcErrors = chartData.some((d) => d.crcErrors !== null);
  const hasDnsLatency = chartData.some((d) => d.dnsLatency !== null);
  const hasWifiRetries = chartData.some((d) => d.wifiRetries !== null);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const itemData = payload[0]?.payload || {};
      const devOrigin = itemData.origin || detectedOrigin;
      const isLive = itemData.isLive;

      return (
        <div className="bg-[#0b0f19] border border-[#22314d] p-3 rounded-xl shadow-2xl text-xs font-mono min-w-[210px]">
          <div className="flex items-center justify-between border-b border-[#1f2c45] pb-1.5 mb-2 gap-2">
            <span className="font-bold text-cyan-300">{label}</span>
            <span
              className={`text-[9px] px-1.5 py-0.2 rounded font-semibold border ${
                isLive
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                  : 'bg-purple-500/20 text-purple-300 border-purple-500/30'
              }`}
            >
              {devOrigin}
            </span>
          </div>

          <div className="space-y-1">
            {payload.map((entry, index) => {
              const val = entry.value;
              const isAvailable = val !== null && val !== undefined;

              return (
                <div key={`item-${index}`} className="flex items-center justify-between gap-3 text-slate-300 py-0.5">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: isAvailable ? entry.color : '#64748b' }}
                    ></span>
                    <span className={isAvailable ? 'text-slate-200' : 'text-slate-500'}>{entry.name}:</span>
                  </span>
                  <span className={`font-bold ${isAvailable ? 'text-white' : 'text-amber-400 font-normal italic'}`}>
                    {isAvailable ? `${val} ${entry.unit || ''}` : 'Not Exposed'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="rounded-2xl bg-[#0f1422] border border-[#1f293d] p-4 shadow-xl space-y-3">
      {/* Chart Navigation Tabs & Provenance Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1f293d] pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white tracking-wide">Live Telemetry Ingestion Metrics</h2>
          <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${originBadge.badgeClass}`}>
            {originBadge.label}
          </span>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40 text-cyan-300">
            {telemetry.length} Device{telemetry.length > 1 ? 's' : ''} Sampled
          </span>
        </div>

        <div className="flex items-center gap-1.5 bg-[#0a0d16] p-1 rounded-xl border border-[#1b2438] text-xs font-medium">
          {/* Tab 1: Latency & Jitter */}
          <button
            onClick={() => setActiveTab('performance')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition-all ${
              activeTab === 'performance'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>Latency & Jitter</span>
            {hasLatency && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>}
          </button>

          {/* Tab 2: Queues & Drops */}
          <button
            onClick={() => setActiveTab('congestion')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition-all ${
              activeTab === 'congestion'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>Queues & Drops</span>
            {hasQueueDrops ? (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            ) : hasPacketLoss ? (
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-mono">
                Loss Only
              </span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-500 font-mono">
                Unexposed
              </span>
            )}
          </button>

          {/* Tab 3: CPU & Hardware */}
          <button
            onClick={() => setActiveTab('infrastructure')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition-all ${
              activeTab === 'infrastructure'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>CPU & Hardware</span>
            {hasCpu || hasMemory || hasCrcErrors ? (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono">
                Not Exposed
              </span>
            )}
          </button>

          {/* Tab 4: RF & DNS */}
          <button
            onClick={() => setActiveTab('services')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition-all ${
              activeTab === 'services'
                ? 'bg-cyan-500 text-black font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>RF & DNS</span>
            {hasDnsLatency || hasWifiRetries ? (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            ) : (
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono">
                Not Exposed
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Target Node, Incident ID, Provenance & Timestamp Status Banner */}
      <div className="flex flex-wrap items-center justify-between text-xs font-mono bg-[#090d16] px-3.5 py-2 rounded-xl border border-[#1b2538] text-slate-400">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Target Node:</span>
          <span className="text-white font-bold">{telemetry[0]?.device_id || 'Unknown'}</span>
          {telemetry[0]?.custom_metrics?.probe_protocol && (
            <span className="px-1.5 py-0.2 rounded bg-cyan-950/80 border border-cyan-800/40 text-cyan-300 text-[10px]">
              {telemetry[0].custom_metrics.probe_protocol}
            </span>
          )}
          {telemetry[0]?.device_status && (
            <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
              telemetry[0].device_status === 'UP' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
            }`}>
              {telemetry[0].device_status}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <div>
            <span className="text-slate-500">INC: </span>
            <span className="text-slate-200 font-semibold">{canonicalReport?.incident_id || 'INC-ACTIVE'}</span>
          </div>
          <div>
            <span className="text-slate-500">Observed: </span>
            <span className="text-slate-300">
              {telemetry[0]?.timestamp ? new Date(telemetry[0].timestamp).toLocaleTimeString() : 'Current'}
            </span>
          </div>
        </div>
      </div>

      {/* Chart Canvas Area */}
      <div className="w-full">
        {/* ========================================================== */}
        {/* TAB 1: LATENCY & JITTER                                    */}
        {/* ========================================================== */}
        {activeTab === 'performance' && (
          <div className="space-y-2">
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
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
                  <Area
                    type="monotone"
                    dataKey="latency"
                    name="Latency (RTT)"
                    stroke="#06b6d4"
                    fillOpacity={1}
                    fill="url(#latencyGrad)"
                    strokeWidth={2}
                    unit="ms"
                    connectNulls={false}
                  />
                  {hasJitter && (
                    <Area
                      type="monotone"
                      dataKey="jitter"
                      name="Jitter (Variance)"
                      stroke="#f59e0b"
                      fillOpacity={1}
                      fill="url(#jitterGrad)"
                      strokeWidth={2}
                      unit="ms"
                      connectNulls={false}
                    />
                  )}
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400 bg-slate-950/60 p-2 rounded-lg border border-slate-800">
              <span className="flex items-center gap-1.5 text-cyan-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
                Latency (RTT): Measured via genuine {originBadge.shortLabel} transport.
              </span>
              <span>
                {hasJitter ? (
                  <span className="text-amber-300">✓ Jitter: Active metric stream</span>
                ) : (
                  <span className="text-slate-500 italic">⊘ Jitter: Not Exposed (Single-probe RTT)</span>
                )}
              </span>
            </div>
          </div>
        )}

        {/* ========================================================== */}
        {/* TAB 2: QUEUES & DROPS                                      */}
        {/* ========================================================== */}
        {activeTab === 'congestion' && (
          <div className="space-y-2">
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1c2538" />
                  <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="left" stroke="#64748b" tick={{ fontSize: 11 }} unit="pkts/s" />
                  <YAxis yAxisId="right" orientation="right" stroke="#64748b" tick={{ fontSize: 11 }} unit="%" />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  {hasQueueDrops && (
                    <Bar
                      yAxisId="left"
                      dataKey="queueDrops"
                      name="Queue Drops"
                      fill="#f43f5e"
                      radius={[4, 4, 0, 0]}
                      unit="pkts/s"
                    />
                  )}
                  {hasUtilization && (
                    <Bar
                      yAxisId="right"
                      dataKey="utilization"
                      name="Link Bandwidth Util"
                      fill="#3b82f6"
                      radius={[4, 4, 0, 0]}
                      unit="%"
                    />
                  )}
                  {hasPacketLoss && (
                    <Bar
                      yAxisId="right"
                      dataKey="packetLoss"
                      name="Packet Loss"
                      fill="#e11d48"
                      radius={[4, 4, 0, 0]}
                      unit="%"
                    />
                  )}
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400 bg-slate-950/60 p-2 rounded-lg border border-slate-800">
              <span className="flex items-center gap-1.5">
                {hasPacketLoss ? (
                  <span className="text-emerald-400">✓ Packet Loss: Measured ({chartData[0]?.packetLoss ?? 0}%)</span>
                ) : (
                  <span className="text-slate-500">⊘ Packet Loss: Not Exposed</span>
                )}
              </span>
              <span>
                {hasQueueDrops || hasUtilization ? (
                  <span className="text-cyan-300">✓ Queue/Utilization: Populated from device operational counters</span>
                ) : (
                  <span className="text-amber-400/90 italic">
                    ⚠️ Queue Drops & Utilization: Not Exposed via ICMP Ping (Requires SNMP/RESTCONF)
                  </span>
                )}
              </span>
            </div>
          </div>
        )}

        {/* ========================================================== */}
        {/* TAB 3: CPU & HARDWARE                                      */}
        {/* ========================================================== */}
        {activeTab === 'infrastructure' && (
          <div className="space-y-2">
            {hasCpu || hasMemory || hasCrcErrors ? (
              <div className="w-full h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1c2538" />
                    <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                    {hasCpu && (
                      <Line
                        type="monotone"
                        dataKey="cpu"
                        name="CPU Load (%)"
                        stroke="#a855f7"
                        strokeWidth={2.5}
                        dot={{ r: 4 }}
                        unit="%"
                        connectNulls={false}
                      />
                    )}
                    {hasMemory && (
                      <Line
                        type="monotone"
                        dataKey="memory"
                        name="Memory Usage (%)"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        unit="%"
                        connectNulls={false}
                      />
                    )}
                    {hasCrcErrors && (
                      <Line
                        type="monotone"
                        dataKey="crcErrors"
                        name="CRC Errors/s"
                        stroke="#ef4444"
                        strokeWidth={2.5}
                        dot={{ r: 4 }}
                        unit="err/s"
                        connectNulls={false}
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="w-full h-64 rounded-xl bg-[#090d18] border border-amber-500/20 p-5 flex flex-col items-center justify-center text-center space-y-2">
                <Cpu className="w-8 h-8 text-amber-400 mb-1" />
                <h4 className="text-sm font-bold text-slate-200 tracking-wide">
                  Hardware Metrics Not Exposed by Protocol
                </h4>
                <p className="text-xs text-slate-400 max-w-lg leading-relaxed">
                  Target device was interrogated via point-to-point ICMP Echo Ping. Internal device CPU load,
                  memory utilization, and optical transceiver CRC counters are unexposed over unauthenticated ICMP ping
                  and were <strong>strictly not fabricated</strong>.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-2 pt-2 text-[11px] font-mono">
                  <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
                    CPU Load: <strong className="text-amber-400 font-semibold">Not Exposed</strong>
                  </span>
                  <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
                    Memory: <strong className="text-amber-400 font-semibold">Not Exposed</strong>
                  </span>
                  <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
                    CRC Errors: <strong className="text-amber-400 font-semibold">Not Exposed</strong>
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono pt-1">
                  Provenance Source: {originBadge.label} (Requires paired SNMPv3 / RESTCONF credentials)
                </span>
              </div>
            )}
          </div>
        )}

        {/* ========================================================== */}
        {/* TAB 4: RF & DNS                                            */}
        {/* ========================================================== */}
        {activeTab === 'services' && (
          <div className="space-y-2">
            {hasDnsLatency || hasWifiRetries ? (
              <div className="w-full h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1c2538" />
                    <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                    {hasDnsLatency && (
                      <Bar
                        dataKey="dnsLatency"
                        name="DNS Response Latency"
                        fill="#ec4899"
                        radius={[4, 4, 0, 0]}
                        unit="ms"
                      />
                    )}
                    {hasWifiRetries && (
                      <Bar
                        dataKey="wifiRetries"
                        name="Wi-Fi 802.11 Retries"
                        fill="#f59e0b"
                        radius={[4, 4, 0, 0]}
                        unit="%"
                      />
                    )}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="w-full h-64 rounded-xl bg-[#090d18] border border-purple-500/20 p-5 flex flex-col items-center justify-center text-center space-y-2">
                <Radio className="w-8 h-8 text-purple-400 mb-1" />
                <h4 className="text-sm font-bold text-slate-200 tracking-wide">
                  Service & Wireless Layer Telemetry Not Exposed
                </h4>
                <p className="text-xs text-slate-400 max-w-lg leading-relaxed">
                  Target device is an IP network gateway. Wireless RF metrics (RSSI/retries) and DNS resolver
                  query latencies were not targeted by this reachability probe and are omitted to avoid false
                  synthetic metrics.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-2 pt-2 text-[11px] font-mono">
                  <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
                    DNS Response: <strong className="text-purple-400 font-semibold">Not Exposed</strong>
                  </span>
                  <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
                    Wi-Fi Retries: <strong className="text-purple-400 font-semibold">Not Exposed</strong>
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono pt-1">
                  Provenance Source: {originBadge.label} (Reachability probe only)
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
