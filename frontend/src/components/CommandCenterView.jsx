import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  fetchExplainableHealthBreakdown,
  fetchProactiveRisks,
  fetchIncidentCorrelations,
  fetchScenarios,
} from '../api/client';

export default function CommandCenterView({ onNavigateToReplay }) {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState('shared_upstream_fault');
  const [healthReport, setHealthReport] = useState(null);
  const [proactiveData, setProactiveData] = useState(null);
  const [correlationData, setCorrelationData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedDevicePenalties, setExpandedDevicePenalties] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'correlations' | 'proactive' | 'health_breakdown'

  // Load scenarios on mount
  useEffect(() => {
    fetchScenarios()
      .then(setScenarios)
      .catch((err) => console.error('Failed to load scenarios:', err));
  }, []);

  // Fetch all intelligence data when selectedScenarioId changes
  const loadIntelligenceData = async (scenarioId) => {
    setLoading(true);
    setError(null);
    try {
      const [hReport, pData, cData] = await Promise.all([
        fetchExplainableHealthBreakdown(scenarioId),
        fetchProactiveRisks(scenarioId),
        fetchIncidentCorrelations(scenarioId),
      ]);
      setHealthReport(hReport);
      setProactiveData(pData);
      setCorrelationData(cData);
    } catch (err) {
      console.error('Failed to load intelligence data:', err);
      setError(err.message || 'Error fetching autonomous intelligence telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIntelligenceData(selectedScenarioId);
  }, [selectedScenarioId]);

  const handleScenarioChange = (e) => {
    const scId = e.target.value;
    setSelectedScenarioId(scId);
  };

  const getScoreColor = (score) => {
    if (score >= 90) return 'text-emerald-400 border-emerald-500/40 bg-emerald-950/20';
    if (score >= 70) return 'text-amber-400 border-amber-500/40 bg-amber-950/20';
    return 'text-rose-400 border-rose-500/40 bg-rose-950/20';
  };

  const getSeverityBadge = (sev) => {
    const s = String(sev || '').toUpperCase();
    if (s.includes('CRITICAL')) {
      return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">CRITICAL</span>;
    }
    if (s.includes('HIGH')) {
      return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-orange-500/20 text-orange-300 border border-orange-500/30">HIGH</span>;
    }
    if (s.includes('MEDIUM')) {
      return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">MEDIUM</span>;
    }
    return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/30">LOW</span>;
  };

  const overallScore = healthReport?.overall_health_score ?? 100.0;
  const compliancePct = healthReport?.sla_compliance_rate_pct ?? 100.0;
  const warningsList = proactiveData?.warnings || [];
  const clustersList = correlationData?.clusters || [];
  const preventedTickets = correlationData?.redundant_tickets_prevented || 0;

  return (
    <div className="space-y-6">
      {/* Top Banner & Scenario Intelligence Selector */}
      <div className="bg-[#0b0e18] border border-slate-800/90 rounded-2xl p-5 shadow-xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                AUTONOMOUS NOC COCKPIT
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800">
                SWARM ACTIVE • CANONICAL v1.0.0
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              Autonomous Network Intelligence Command Center
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              Real-time cross-incident topological correlation, predictive SLA drift warnings, and auditable point-deduction health diagnostics evaluated by five cooperating agents.
            </p>
          </div>

          {/* Scenario Picker & Actions */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex flex-col">
              <label className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-1">
                Telemetry Context Scenario
              </label>
              <select
                value={selectedScenarioId}
                onChange={handleScenarioChange}
                className="bg-[#0f172a] border border-slate-700 text-slate-100 text-xs rounded-lg px-3 py-2 font-medium focus:outline-none focus:border-cyan-500 transition-colors cursor-pointer"
              >
                {scenarios.map((sc) => (
                  <option key={sc.id} value={sc.id}>
                    {sc.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => loadIntelligenceData(selectedScenarioId)}
              disabled={loading}
              className="mt-4 px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs rounded-lg shadow-md shadow-cyan-950/40 transition-all flex items-center gap-2 disabled:opacity-50"
            >
              <span>{loading ? 'Analyzing Swarm...' : '↻ Refresh Intelligence'}</span>
            </button>
          </div>
        </div>

        {/* Intelligence Sub-Tabs */}
        <div className="flex flex-wrap items-center gap-2 mt-5 pt-3.5 border-t border-slate-800/80 text-xs font-medium">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'overview'
                ? 'bg-slate-800 text-white font-bold border border-slate-700 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            📊 Executive Cockpit
          </button>
          <button
            onClick={() => setActiveTab('correlations')}
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'correlations'
                ? 'bg-slate-800 text-white font-bold border border-slate-700 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🔗 Cross-Incident Correlation
            {clustersList.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-500/30 text-indigo-300 font-bold">
                {clustersList.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('proactive')}
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'proactive'
                ? 'bg-slate-800 text-white font-bold border border-slate-700 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🔮 Proactive Risk Forecast
            {warningsList.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500/30 text-amber-300 font-bold">
                {warningsList.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('health_breakdown')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'health_breakdown'
                ? 'bg-slate-800 text-white font-bold border border-slate-700 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            📋 Explainable Health Audit
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/60 border border-rose-800/80 text-rose-300 px-4 py-3 rounded-xl text-xs font-mono">
          Intelligence Query Error: {error}
        </div>
      )}

      {/* Top 4 Executive KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Explainable Network Health Score */}
        <div className="bg-[#0b0e18] border border-slate-800/90 rounded-xl p-4 flex flex-col justify-between shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              Composite Health Score
            </span>
            <span className="text-lg">🛡️</span>
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className={`text-3xl font-extrabold ${overallScore >= 80 ? 'text-emerald-400' : overallScore >= 60 ? 'text-amber-400' : 'text-rose-400'}`}>
              {overallScore.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400">/ 100</span>
            <span className={`ml-auto px-2 py-0.5 rounded text-[10px] font-bold ${overallScore >= 80 ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'}`}>
              {healthReport?.status || 'DEGRADED'}
            </span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${overallScore >= 80 ? 'bg-emerald-500' : overallScore >= 60 ? 'bg-amber-500' : 'bg-rose-500'}`}
              style={{ width: `${Math.min(100, Math.max(0, overallScore))}%` }}
            />
          </div>
          <span className="text-[10px] text-slate-400 mt-2">
            {compliancePct.toFixed(1)}% golden SLA compliance across {healthReport?.total_devices_evaluated || 8} nodes
          </span>
        </div>

        {/* KPI 2: Cross-Incident Correlated Clusters */}
        <div className="bg-[#0b0e18] border border-slate-800/90 rounded-xl p-4 flex flex-col justify-between shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              Correlated Fault Clusters
            </span>
            <span className="text-lg">🔗</span>
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-indigo-400">
              {clustersList.length}
            </span>
            <span className="text-xs text-slate-400">active cluster(s)</span>
            <span className="ml-auto px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
              TOPOLOGICAL MATCH
            </span>
          </div>
          <div className="text-[11px] text-emerald-400 flex items-center gap-1 font-semibold">
            <span>✓</span>
            <span>{preventedTickets} redundant technician tickets eliminated</span>
          </div>
          <span className="text-[10px] text-slate-400 mt-1">
            Grouped by shared upstream distribution choke-points
          </span>
        </div>

        {/* KPI 3: Proactive Risks Detected */}
        <div className="bg-[#0b0e18] border border-slate-800/90 rounded-xl p-4 flex flex-col justify-between shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              Proactive Drift Warnings
            </span>
            <span className="text-lg">🔮</span>
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-400">
              {warningsList.length}
            </span>
            <span className="text-xs text-slate-400">impending breaches</span>
            <span className="ml-auto px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
              PRE-THRESHOLD
            </span>
          </div>
          <div className="text-[11px] text-slate-300">
            Earliest predicted breach: <strong className="text-amber-400 font-mono">
              {warningsList.length > 0 ? `${Math.min(...warningsList.map(w => w.time_to_breach_minutes))} min` : 'None'}
            </strong>
          </div>
          <span className="text-[10px] text-slate-400 mt-1">
            Evaluated via deterministic linear trend extrapolation
          </span>
        </div>

        {/* KPI 4: Swarm Consensus & Bounded Trace */}
        <div className="bg-[#0b0e18] border border-slate-800/90 rounded-xl p-4 flex flex-col justify-between shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              Agent Swarm Convergence
            </span>
            <span className="text-lg">🤖</span>
          </div>
          <div className="my-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-cyan-400">
              5 / 5
            </span>
            <span className="text-xs text-slate-400">agents aligned</span>
            <span className="ml-auto px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
              CONSENSUS
            </span>
          </div>
          <div className="text-[11px] text-slate-300">
            Investigation Rounds: <span className="font-mono text-cyan-400 font-bold">2 max (bounded)</span>
          </div>
          <span className="text-[10px] text-slate-400 mt-1">
            Zero recursive agent loops; deterministic stopping condition
          </span>
        </div>
      </div>

      {/* Main Tab Views */}
      <AnimatePresence mode="wait">
        {/* VIEW 1: EXECUTIVE COCKPIT OVERVIEW */}
        {activeTab === 'overview' && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            {/* Left 2 Cols: Cross-Incident Correlated Clusters Highlight */}
            <div className="lg:col-span-2 space-y-6">
              {/* Highlight Card: Cross-Incident Upstream Bottleneck */}
              <div className="bg-[#0d121f] border border-[#1f293d] rounded-2xl p-5 shadow-xl">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-sm font-bold text-white flex items-center gap-2">
                      <span className="text-indigo-400">🔗</span>
                      Cross-Incident Topology Correlation & Upstream Choke-Points
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Downstream edge switch and wireless alerts grouped by shared upstream infrastructure ancestor.
                    </p>
                  </div>
                  <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-indigo-950/60 text-indigo-300 border border-indigo-800">
                    {clustersList.length} Cluster(s) Active
                  </span>
                </div>

                {clustersList.length === 0 ? (
                  <div className="text-center py-10 text-slate-400 text-xs bg-slate-900/40 rounded-xl border border-slate-800">
                    No active incident clusters detected for the current telemetry profile.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {clustersList.map((cluster) => (
                      <div
                        key={cluster.cluster_id}
                        className="bg-[#0a0e18] border border-indigo-900/50 rounded-xl p-4 hover:border-indigo-500/60 transition-all shadow-md"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                              {cluster.cluster_id}
                            </span>
                            <h3 className="text-sm font-bold text-white">
                              {cluster.title}
                            </h3>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800 px-2 py-0.5 rounded">
                              {cluster.prevented_redundant_actions || cluster.prevented_redundant_actions_count || 1} Redundant Action(s) Suppressed
                            </span>
                            <span className="text-xs font-bold text-cyan-400">
                              {Math.round((cluster.relationship_confidence || cluster.confidence || 0.9) * 100)}% Conf
                            </span>
                          </div>
                        </div>

                        {/* Candidate Upstream Root Cause */}
                        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-lg mb-3">
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="font-semibold text-slate-400">Single Upstream Root Cause:</span>
                            <span className="font-mono text-cyan-400 font-bold">{cluster.primary_device || cluster.primary_suspected_device}</span>
                          </div>
                          <p className="text-xs text-slate-200">
                            {cluster.root_cause_candidate || cluster.candidate_root_cause}
                          </p>
                        </div>

                        {/* Affected Downstream Nodes */}
                        <div className="text-xs mb-3">
                          <span className="text-slate-400 font-semibold mr-2">Downstream Symptom Leaves:</span>
                          <div className="inline-flex flex-wrap gap-1.5 mt-1">
                            {cluster.implicated_devices.map((dev) => {
                              const isRoot = dev === (cluster.primary_device || cluster.primary_suspected_device);
                              return (
                                <span
                                  key={dev}
                                  className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold ${
                                    isRoot
                                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                                      : 'bg-slate-800 text-slate-300 border border-slate-700'
                                  }`}
                                >
                                  {isRoot ? `⭐ Upstream: ${dev}` : `Cascaded: ${dev}`}
                                </span>
                              );
                            })}
                          </div>
                        </div>

                        {/* Recommended Unified Action */}
                        <div className="bg-indigo-950/30 border border-indigo-800/40 p-2.5 rounded-lg text-xs text-indigo-200 flex items-start gap-2">
                          <span className="text-sm">🎯</span>
                          <div>
                            <strong className="text-indigo-300">Unified NOC Action: </strong>
                            {cluster.recommended_unified_remediation || cluster.recommended_unified_action}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Proactive Risk Early-Warning Highlight Cards */}
              <div className="bg-[#0d121f] border border-[#1f293d] rounded-2xl p-5 shadow-xl">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-sm font-bold text-white flex items-center gap-2">
                      <span className="text-amber-400">🔮</span>
                      Top Proactive Degradation Warnings (Next 10-20 Mins)
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Sub-threshold metric drift caught prior to catastrophic service interruption.
                    </p>
                  </div>
                  <button
                    onClick={() => setActiveTab('proactive')}
                    className="text-xs text-cyan-400 hover:text-cyan-300 underline"
                  >
                    View All ({warningsList.length}) →
                  </button>
                </div>

                {warningsList.length === 0 ? (
                  <div className="text-center py-8 text-slate-400 text-xs bg-slate-900/40 rounded-xl border border-slate-800">
                    All telemetry metrics within stable non-drifting bounds.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {warningsList.slice(0, 4).map((w) => (
                      <div
                        key={w.warning_id}
                        className="bg-[#0a0e18] border border-slate-800 hover:border-amber-500/40 p-3.5 rounded-xl transition-all flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between gap-1 mb-2">
                            <span className="text-xs font-mono font-bold text-cyan-400">
                              {w.device_id}
                            </span>
                            {getSeverityBadge(w.severity)}
                          </div>
                          <h4 className="text-xs font-bold text-white mb-1.5 line-clamp-1">
                            {w.title}
                          </h4>
                          <p className="text-[11px] text-slate-400 mb-2 line-clamp-2">
                            {w.expected_impact}
                          </p>
                        </div>

                        <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-slate-400">Current / 10m Proj:</span>
                            <span className="font-mono text-white font-semibold">
                              {w.current_value} {w.unit} → <span className="text-amber-400 font-bold">{w.projected_value_10m}</span> {w.unit}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-slate-400">Estimated Breach:</span>
                            <span className="font-mono text-rose-400 font-bold">
                              {w.time_to_breach_minutes <= 1 ? 'Immediate / Active' : `~${w.time_to_breach_minutes} mins`}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right 1 Col: Explainable Health Audit & Swarm Intelligence Trace */}
            <div className="space-y-6">
              {/* Device Health Breakdown List */}
              <div className="bg-[#0d121f] border border-[#1f293d] rounded-2xl p-5 shadow-xl">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <span>📋</span>
                    Auditable Health Audit
                  </h2>
                  <span className="text-[11px] font-mono text-slate-400">
                    {healthReport?.device_breakdowns?.length || 0} Devices
                  </span>
                </div>

                <div className="space-y-3">
                  {healthReport?.device_breakdowns?.map((dev) => (
                    <div
                      key={dev.device_id}
                      onClick={() => setExpandedDevicePenalties(expandedDevicePenalties === dev.device_id ? null : dev.device_id)}
                      className={`p-3 rounded-xl border transition-all cursor-pointer ${
                        dev.health_score < 70
                          ? 'bg-rose-950/20 border-rose-900/50 hover:border-rose-700'
                          : dev.health_score < 90
                          ? 'bg-amber-950/20 border-amber-900/50 hover:border-amber-700'
                          : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold text-white">
                            {dev.device_id}
                          </span>
                          <span className="text-[10px] text-slate-400">{dev.role}</span>
                        </div>
                        <span
                          className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                            dev.health_score < 70
                              ? 'text-rose-400 border-rose-500/30 bg-rose-500/10'
                              : dev.health_score < 90
                              ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
                              : 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                          }`}
                        >
                          {dev.health_score.toFixed(0)}%
                        </span>
                      </div>

                      {/* Health Bar */}
                      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mb-2">
                        <div
                          className={`h-full ${
                            dev.health_score >= 90
                              ? 'bg-emerald-500'
                              : dev.health_score >= 70
                              ? 'bg-amber-500'
                              : 'bg-rose-500'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(0, dev.health_score))}%` }}
                        />
                      </div>

                      {/* Penalties Summary */}
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>
                          {dev.penalties.length > 0 ? (
                            <span className="text-rose-400 font-semibold">
                              -{dev.penalties.reduce((acc, p) => acc + p.points_deducted, 0)} pts ({dev.penalties.length} breaches)
                            </span>
                          ) : (
                            <span className="text-emerald-400">Zero SLA breaches</span>
                          )}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedDevicePenalties(expandedDevicePenalties === dev.device_id ? null : dev.device_id);
                          }}
                          className="text-[10px] text-cyan-400 hover:text-cyan-300 font-semibold cursor-pointer"
                        >
                          {expandedDevicePenalties === dev.device_id ? '▲ Hide' : '▼ Details'}
                        </button>
                      </div>

                      {/* Expanded Itemized Penalty Audit */}
                      {expandedDevicePenalties === dev.device_id && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          className="mt-3 pt-2.5 border-t border-slate-800/80 space-y-2 text-[11px]"
                        >
                          {dev.penalties.length === 0 ? (
                            <div className="text-emerald-400 text-[10px]">
                              All performance, interface, and service metrics strictly within SLA baselines.
                            </div>
                          ) : (
                            dev.penalties.map((pen, idx) => (
                              <div key={idx} className="bg-slate-900/90 p-2 rounded border border-rose-900/40">
                                <div className="flex items-center justify-between text-rose-300 font-semibold">
                                  <span>{pen.metric_name}</span>
                                  <span className="font-mono text-rose-400">-{pen.points_deducted} pts</span>
                                </div>
                                <div className="text-[10px] text-slate-400 mt-0.5">
                                  Observed: <strong className="text-white">{pen.observed_value} {pen.unit}</strong> (Limit: {pen.sla_limit} {pen.unit})
                                </div>
                                <div className="text-[10px] text-slate-300 mt-1 italic">
                                  "{pen.reason}"
                                </div>
                              </div>
                            ))
                          )}
                        </motion.div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Swarm Autonomous Investigation Trace Audit Card */}
              <div className="bg-[#0d121f] border border-[#1f293d] rounded-2xl p-5 shadow-xl">
                <h2 className="text-sm font-bold text-white flex items-center gap-2 mb-3">
                  <span>🧠</span>
                  Agent Swarm Reasoning Trace
                </h2>
                <div className="space-y-3 text-xs">
                  <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider mb-1">
                      Termination Condition
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                        SUFFICIENT_PROOF
                      </span>
                      <span className="text-slate-200 font-semibold">Evidential Consensus</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Swarm terminated dialogue deterministically within 2 interrogation rounds upon achieving unanimous Bayesian evidence convergence.
                    </p>
                  </div>

                  <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider mb-1">
                      Dynamic Priority Dispatch Order
                    </span>
                    <div className="flex items-center gap-1.5 font-mono text-[11px] text-cyan-400">
                      <span>infra-agent-01</span>
                      <span className="text-slate-500">→</span>
                      <span>perf-agent-01</span>
                      <span className="text-slate-500">→</span>
                      <span>conn-agent-01</span>
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1">
                      Priority dynamically adjusted based on CRC discards and physical layer telemetry severity.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* VIEW 2: FULL CROSS-INCIDENT CORRELATION TAB */}
        {activeTab === 'correlations' && (
          <motion.div
            key="correlations"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            <div className="bg-[#0d121f] border border-[#1f293d] rounded-2xl p-6 shadow-xl">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <span className="text-indigo-400">🔗</span>
                    Cross-Incident Correlation Engine
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Automated topological reachability analysis groups concurrent downstream incidents to their common upstream root cause, preventing ticket duplication.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Redundant Tickets Prevented</span>
                    <span className="text-xl font-bold font-mono text-emerald-400">{preventedTickets} tickets</span>
                  </div>
                </div>
              </div>

              {clustersList.length === 0 ? (
                <div className="text-center py-12 text-slate-400 text-sm">
                  No multi-device incident clusters found for this scenario.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-6">
                  {clustersList.map((cluster) => (
                    <div
                      key={cluster.cluster_id}
                      className="bg-[#0a0e18] border border-indigo-900/60 rounded-2xl p-6 shadow-lg relative overflow-hidden"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                        <div className="flex items-center gap-3">
                          <span className="px-3 py-1 rounded-lg text-xs font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                            {cluster.cluster_id}
                          </span>
                          <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            {cluster.relationship_type}
                          </span>
                        </div>
                        <span className="text-sm font-mono font-bold text-cyan-400">
                          Consensus Confidence: {Math.round((cluster.relationship_confidence || cluster.confidence || 0.9) * 100)}%
                        </span>
                      </div>

                      <h3 className="text-base font-bold text-white mb-2">
                        {cluster.title}
                      </h3>
                      <p className="text-xs text-slate-300 mb-6 leading-relaxed">
                        {cluster.correlation_reasoning || cluster.correlation_explanation}
                      </p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                            Topological Root Cause Node
                          </span>
                          <div className="text-sm font-bold text-rose-400 flex items-center gap-2 mb-1">
                            <span>⭐</span>
                            <span>{cluster.primary_device || cluster.primary_suspected_device}</span>
                          </div>
                          <p className="text-xs text-slate-300">
                            {cluster.root_cause_candidate || cluster.candidate_root_cause}
                          </p>
                        </div>

                        <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                            Impacted Downstream Nodes ({cluster.implicated_devices.length})
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {cluster.implicated_devices.map((d) => {
                              const isRoot = d === (cluster.primary_device || cluster.primary_suspected_device);
                              return (
                                <span
                                  key={d}
                                  className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold ${
                                    isRoot
                                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                                      : 'bg-slate-800 text-slate-300 border border-slate-700'
                                  }`}
                                >
                                  {isRoot ? `⭐ Upstream: ${d}` : `Cascaded: ${d}`}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      </div>

                      <div className="bg-indigo-950/40 border border-indigo-800/60 p-4 rounded-xl flex items-start gap-3">
                        <span className="text-xl">🛠️</span>
                        <div>
                          <strong className="text-sm font-bold text-indigo-300 block mb-1">
                            Actionable Unified Remediation
                          </strong>
                          <p className="text-xs text-slate-200">
                            {cluster.recommended_unified_remediation || cluster.recommended_unified_action}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* VIEW 3: FULL PROACTIVE RADAR TAB */}
        {activeTab === 'proactive' && (
          <motion.div
            key="proactive"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            <div className="bg-[#0d121f] border border-[#1f293d] rounded-2xl p-6 shadow-xl">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <span className="text-amber-400">🔮</span>
                    Proactive Telemetry Trend & Pre-Breach Warning Radar
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Multi-point linear regression and drift rate modeling to preempt network outages before SLA violations occur.
                  </p>
                </div>
                <span className="text-xs font-mono px-3 py-1.5 rounded-lg bg-amber-950/60 text-amber-300 border border-amber-800">
                  {warningsList.length} Warning(s) Active
                </span>
              </div>

              {warningsList.length === 0 ? (
                <div className="text-center py-12 text-slate-400 text-sm">
                  No metric drift detected across any monitored device.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {warningsList.map((w) => (
                    <div
                      key={w.warning_id}
                      className="bg-[#0a0e18] border border-slate-800 hover:border-amber-500/50 p-5 rounded-2xl transition-all shadow-lg flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-3">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-bold text-cyan-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                              {w.device_id}
                            </span>
                            <span className="text-xs font-mono text-slate-400">
                              {w.metric}
                            </span>
                          </div>
                          {getSeverityBadge(w.severity)}
                        </div>

                        <h3 className="text-sm font-bold text-white mb-2">
                          {w.title}
                        </h3>
                        <p className="text-xs text-slate-300 mb-4 leading-relaxed">
                          {w.expected_impact}
                        </p>
                      </div>

                      <div className="space-y-3 pt-3 border-t border-slate-800/80">
                        {/* Telemetry Numbers */}
                        <div className="grid grid-cols-3 gap-2 bg-slate-900/80 p-3 rounded-xl border border-slate-800 text-center">
                          <div>
                            <span className="text-[10px] text-slate-400 block">Current</span>
                            <span className="text-xs font-bold font-mono text-white">
                              {w.current_value} {w.unit}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">10m Projection</span>
                            <span className="text-xs font-bold font-mono text-amber-400">
                              {w.projected_value_10m} {w.unit}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block">Time to Breach</span>
                            <span className="text-xs font-bold font-mono text-rose-400">
                              {w.time_to_breach_minutes <= 1 ? 'Immediate' : `${w.time_to_breach_minutes}m`}
                            </span>
                          </div>
                        </div>

                        {/* Preventive Runbook */}
                        <div className="bg-amber-950/20 border border-amber-900/40 p-3 rounded-xl text-xs text-amber-200">
                          <strong className="text-amber-300 block mb-1">Preventive Runbook:</strong>
                          {w.preventive_remediation}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* VIEW 4: FULL EXPLAINABLE HEALTH AUDIT TAB */}
        {activeTab === 'health_breakdown' && (
          <motion.div
            key="health_breakdown"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            <div className="bg-[#0d121f] border border-[#1f293d] rounded-2xl p-6 shadow-xl">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-800">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <span>📋</span>
                    Itemized SLA Health Audit Methodology
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Every point deducted is transparently mapped to an empirical metric SLA breach. Zero black-box scoring.
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-400 block">Overall Health Score</span>
                  <span className="text-2xl font-bold font-mono text-white">
                    {overallScore.toFixed(1)} / 100
                  </span>
                </div>
              </div>

              <div className="space-y-4">
                {healthReport?.device_breakdowns?.map((dev) => (
                  <div
                    key={dev.device_id}
                    className="bg-[#0a0e18] border border-slate-800 rounded-xl p-5 shadow-md"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-bold text-white font-mono">{dev.device_id}</span>
                        <span className="text-xs text-slate-400">({dev.device_name} — {dev.role})</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono text-slate-400">
                          SLA Status: <strong className={dev.sla_status === 'COMPLIANT' ? 'text-emerald-400' : 'text-rose-400'}>{dev.sla_status}</strong>
                        </span>
                        <span className="text-sm font-bold font-mono px-3 py-0.5 rounded-lg border text-white bg-slate-900 border-slate-700">
                          Score: {dev.health_score.toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    {/* Penalties Itemization */}
                    {dev.penalties.length === 0 ? (
                      <div className="text-xs text-emerald-400 bg-emerald-950/20 border border-emerald-900/30 p-3 rounded-lg">
                        ✓ All performance metrics compliant with golden SLA baselines. Zero deductions.
                      </div>
                    ) : (
                      <div className="space-y-2 mt-2">
                        {dev.penalties.map((pen, pIdx) => (
                          <div
                            key={pIdx}
                            className="bg-rose-950/30 border border-rose-900/50 p-3 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs"
                          >
                            <div>
                              <strong className="text-rose-300 font-mono">{pen.metric_name}: </strong>
                              <span className="text-slate-300">{pen.reason}</span>
                            </div>
                            <div className="flex items-center gap-4 text-right">
                              <span className="text-slate-400 font-mono">
                                Observed: {pen.observed_value} {pen.unit} (Limit: {pen.sla_limit} {pen.unit})
                              </span>
                              <span className="font-mono text-rose-400 font-bold px-2 py-0.5 rounded bg-rose-950 border border-rose-800">
                                -{pen.points_deducted} pts
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
