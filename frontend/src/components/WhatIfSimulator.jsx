import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  fetchRemediationStrategies,
  simulateRemediation,
  compareRemediationStrategies,
} from '../api/client';

export default function WhatIfSimulator({ diagnosticResult, onSimulationApplied }) {
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState('');
  const [comparisonMatrix, setComparisonMatrix] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [activeTab, setActiveTab] = useState('simulate'); // 'simulate' | 'compare'
  const [error, setError] = useState(null);

  const incidentId = diagnosticResult?.incident_id || 'INC-DEMO-01';
  const rootCause = diagnosticResult?.suspected_root_cause || 'Control Plane Processor Saturation';
  const targetDevice = diagnosticResult?.affected_devices?.[0] || 'Core-Router-01';
  const currentTelemetry = diagnosticResult?.telemetry?.[0] || {
    cpu_utilization_pct: 99.4,
    latency_ms: 115.0,
    packet_loss_pct: 4.2,
    utilization_pct: 14.0,
    queue_drops_per_sec: 0.0,
  };

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const strats = await fetchRemediationStrategies(rootCause, targetDevice);
        setStrategies(strats);
        if (strats.length > 0) {
          setSelectedStrategyId(strats[0].strategy_id);
        }

        const matrix = await compareRemediationStrategies({
          incident_id: incidentId,
          target_device: targetDevice,
          root_cause: rootCause,
          current_telemetry: currentTelemetry,
        });
        setComparisonMatrix(matrix);
      } catch (err) {
        setError(err.message || 'Failed to load simulator data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [rootCause, targetDevice, incidentId]);

  const handleRunSimulation = async () => {
    if (!selectedStrategyId) return;
    setSimulating(true);
    setError(null);
    try {
      const result = await simulateRemediation({
        incident_id: incidentId,
        strategy_id: selectedStrategyId,
        target_device: targetDevice,
        root_cause: rootCause,
        current_telemetry: currentTelemetry,
      });
      setSimulationResult(result);
      if (onSimulationApplied) {
        onSimulationApplied(result);
      }
    } catch (err) {
      setError(err.message || 'Simulation execution failed');
    } finally {
      setSimulating(false);
    }
  };

  const selectedStrategy = strategies.find((s) => s.strategy_id === selectedStrategyId) || strategies[0];

  const getRiskBadge = (risk) => {
    const r = (risk || 'LOW').toUpperCase();
    if (r === 'LOW') return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">LOW RISK</span>;
    if (r === 'MEDIUM') return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">MEDIUM RISK</span>;
    return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">HIGH RISK</span>;
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </span>
            <h2 className="text-lg font-bold text-slate-100">What-If Remediation Simulator & Strategy Comparison</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Simulate expected data-plane recovery, assess operational tradeoffs, and evaluate alternatives prior to production deployment.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-medium">
          <button
            onClick={() => setActiveTab('simulate')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === 'simulate' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🔬 Simulation & Impact
          </button>
          <button
            onClick={() => setActiveTab('compare')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === 'compare' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ⚖️ Strategy Comparison Matrix
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-2">
          <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs">Loading deterministic remediation models...</span>
        </div>
      ) : (
        <>
          {activeTab === 'simulate' && (
            <div className="space-y-6">
              {/* Context Summary Bar */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-slate-950/70 p-3 rounded-lg border border-slate-800/80 text-xs">
                <div>
                  <span className="text-slate-500 block uppercase font-mono tracking-wider">Target Incident</span>
                  <span className="font-semibold text-slate-200">{incidentId}</span>
                </div>
                <div>
                  <span className="text-slate-500 block uppercase font-mono tracking-wider">Diagnosed Root Cause</span>
                  <span className="font-semibold text-amber-300">{rootCause}</span>
                </div>
                <div>
                  <span className="text-slate-500 block uppercase font-mono tracking-wider">Implicated Device</span>
                  <span className="font-mono text-cyan-300">{targetDevice}</span>
                </div>
              </div>

              {/* Strategy Selection Cards */}
              <div>
                <label className="block text-xs font-mono uppercase text-slate-400 tracking-wider mb-2">
                  Select Remediation Strategy to Simulate:
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {strategies.map((strat, idx) => {
                    const isSelected = strat.strategy_id === selectedStrategyId;
                    return (
                      <motion.div
                        key={strat.strategy_id}
                        whileHover={{ scale: 1.01 }}
                        onClick={() => setSelectedStrategyId(strat.strategy_id)}
                        className={`cursor-pointer p-4 rounded-xl border transition-all text-left flex flex-col justify-between ${
                          isSelected
                            ? 'bg-cyan-950/40 border-cyan-500/80 shadow-lg shadow-cyan-900/20'
                            : 'bg-slate-950/50 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-mono text-cyan-400 font-bold">Strategy {String.fromCharCode(65 + idx)}</span>
                            {getRiskBadge(strat.operational_risk)}
                          </div>
                          <h4 className="text-sm font-semibold text-slate-100 mb-1">{strat.name}</h4>
                          <p className="text-xs text-slate-400 line-clamp-2 mb-3">{strat.description}</p>
                        </div>

                        <div className="border-t border-slate-800/80 pt-2 flex items-center justify-between text-xs text-slate-400">
                          <span>⏱️ {strat.recovery_time_seconds}s Recovery</span>
                          <span className="text-emerald-400 font-semibold">{strat.effectiveness_pct}% Effect</span>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </div>

              {/* Selected Strategy Details & Action */}
              {selectedStrategy && (
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-slate-200">{selectedStrategy.name}</h3>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">Category: {selectedStrategy.category} | Intervention: {selectedStrategy.intervention_type}</p>
                    </div>

                    <button
                      onClick={handleRunSimulation}
                      disabled={simulating}
                      className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs rounded-lg shadow-lg shadow-cyan-900/30 flex items-center gap-2 transition-all disabled:opacity-50"
                    >
                      {simulating ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          <span>Computing Telemetry Deltas...</span>
                        </>
                      ) : (
                        <>
                          <span>⚡</span>
                          <span>Execute What-If Simulation</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* CLI Command & Rollback Preview */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                    <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block text-[10px] uppercase">Remediation CLI Syntax</span>
                      <span className="text-cyan-300 break-all">{selectedStrategy.command}</span>
                    </div>
                    <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                      <span className="text-slate-500 block text-[10px] uppercase">Rollback Guard Procedure</span>
                      <span className="text-amber-300 break-all">{selectedStrategy.rollback_command}</span>
                    </div>
                  </div>

                  {/* Tradeoffs Explanation */}
                  <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800/80 text-xs">
                    <span className="text-slate-400 font-semibold block mb-1">⚖️ Trade-off Rationale:</span>
                    <p className="text-slate-300 leading-relaxed">{selectedStrategy.tradeoffs}</p>
                  </div>
                </div>
              )}

              {/* Simulation Result / Before & After Telemetry Diff */}
              <AnimatePresence>
                {simulationResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -15 }}
                    className="space-y-4 bg-slate-950/80 p-5 rounded-xl border border-cyan-500/40 shadow-xl"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                          <h3 className="text-sm font-bold text-slate-100">Simulation Projections: {simulationResult.strategy_name}</h3>
                        </div>
                        <span className="text-xs text-slate-400 font-mono">Sim ID: {simulationResult.simulation_id}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          {simulationResult.recovery_status}
                        </span>
                        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                          SLA: {simulationResult.sla_status_after}
                        </span>
                      </div>
                    </div>

                    {/* Health Score Transition */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-400">Current Health Index</span>
                          <span className="text-rose-400 font-bold font-mono">{simulationResult.device_health_before} / 100</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                          <div className="bg-rose-500 h-2 rounded-full" style={{ width: `${simulationResult.device_health_before}%` }}></div>
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-400">Projected Post-Remediation Health</span>
                          <span className="text-emerald-400 font-bold font-mono">{simulationResult.device_health_after} / 100</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                          <div className="bg-emerald-500 h-2 rounded-full transition-all duration-1000" style={{ width: `${simulationResult.device_health_after}%` }}></div>
                        </div>
                      </div>
                    </div>

                    {/* Telemetry Before vs After Comparison Grid */}
                    <div>
                      <h4 className="text-xs font-mono uppercase text-slate-400 tracking-wider mb-2">Observed vs Simulated Telemetry Deltas</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {Object.entries(simulationResult.telemetry_deltas).map(([metric, data]) => {
                          const isImproved = data.status === 'IMPROVED';
                          const isDegraded = data.status === 'DEGRADED';
                          return (
                            <div key={metric} className="p-3 bg-slate-900 rounded-lg border border-slate-800/90 text-xs">
                              <span className="text-slate-500 block text-[10px] font-mono uppercase truncate mb-1">
                                {metric.replace(/_/g, ' ')}
                              </span>
                              <div className="flex items-baseline justify-between mb-1">
                                <span className="text-slate-400 line-through font-mono text-[11px]">{data.before}</span>
                                <span className="text-slate-100 font-bold font-mono text-sm">{data.after}</span>
                              </div>
                              <div className="flex items-center justify-between text-[10px]">
                                <span className={isImproved ? 'text-emerald-400 font-bold' : isDegraded ? 'text-rose-400 font-bold' : 'text-slate-400'}>
                                  {data.delta > 0 ? `+${data.delta}` : data.delta} ({data.pct_change > 0 ? `+${data.pct_change}%` : `${data.pct_change}%`})
                                </span>
                                <span className={`px-1.5 py-0.2 rounded font-semibold ${
                                  isImproved ? 'bg-emerald-500/20 text-emerald-300' : isDegraded ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-800 text-slate-400'
                                }`}>
                                  {data.status}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Expected Benefits & Risks */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                      <div className="p-3 bg-emerald-950/20 border border-emerald-500/20 rounded-lg space-y-1.5">
                        <span className="text-emerald-400 font-bold block">✅ Expected Verification Benefits</span>
                        <ul className="space-y-1 text-slate-300 list-disc list-inside">
                          {simulationResult.expected_benefits.map((b, i) => (
                            <li key={i}>{b}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="p-3 bg-rose-950/20 border border-rose-500/20 rounded-lg space-y-1.5">
                        <span className="text-rose-400 font-bold block">⚠️ Potential Operational Risks</span>
                        <ul className="space-y-1 text-slate-300 list-disc list-inside">
                          {simulationResult.potential_risks.length > 0 ? (
                            simulationResult.potential_risks.map((r, i) => <li key={i}>{r}</li>)
                          ) : (
                            <li className="text-slate-500 italic">No significant risks identified for automated policing</li>
                          )}
                        </ul>
                      </div>
                    </div>

                    {/* Assumptions and Limitations */}
                    <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1">
                      <span className="font-semibold text-slate-300 block">📌 Simulation Model Assumptions:</span>
                      <ul className="list-disc list-inside space-y-0.5">
                        {simulationResult.assumptions.map((a, i) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {activeTab === 'compare' && comparisonMatrix && (
            <div className="space-y-6">
              {/* Summary Card */}
              <div className="p-4 bg-cyan-950/30 border border-cyan-500/30 rounded-xl text-xs space-y-2">
                <div className="flex items-center gap-2 text-cyan-300 font-bold">
                  <span>💡</span>
                  <span>Recommendation Rationale:</span>
                </div>
                <p className="text-slate-200 leading-relaxed">{comparisonMatrix.recommendation_rationale}</p>
                <p className="text-slate-400 text-[11px] font-mono">{comparisonMatrix.comparison_summary}</p>
              </div>

              {/* Side-by-Side Comparison Table */}
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
                <table className="w-full text-left text-xs text-slate-300 border-collapse">
                  <thead>
                    <tr className="bg-slate-900/90 text-slate-400 font-mono uppercase text-[11px] border-b border-slate-800">
                      <th className="p-3.5">Remediation Strategy</th>
                      <th className="p-3.5">Category</th>
                      <th className="p-3.5">Risk Level</th>
                      <th className="p-3.5">Recovery Time</th>
                      <th className="p-3.5">Intervention</th>
                      <th className="p-3.5">Effectiveness</th>
                      <th className="p-3.5">Key Trade-off</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 font-sans">
                    {comparisonMatrix.strategies.map((strat, idx) => {
                      const isRecommended = strat.strategy_id === comparisonMatrix.recommended_strategy_id;
                      return (
                        <tr
                          key={strat.strategy_id}
                          className={`transition-colors ${
                            isRecommended ? 'bg-cyan-950/20 hover:bg-cyan-950/30' : 'hover:bg-slate-900/50'
                          }`}
                        >
                          <td className="p-3.5 font-semibold text-slate-100">
                            <div className="flex items-center gap-1.5">
                              {isRecommended && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-cyan-500 text-slate-950">
                                  BEST
                                </span>
                              )}
                              <span>{strat.name}</span>
                            </div>
                            <span className="text-[10px] font-mono text-slate-500 block mt-0.5">{strat.strategy_id}</span>
                          </td>
                          <td className="p-3.5 text-slate-400 font-mono text-[11px]">{strat.category}</td>
                          <td className="p-3.5">{getRiskBadge(strat.operational_risk)}</td>
                          <td className="p-3.5 font-mono text-slate-200">~{strat.recovery_time_seconds}s</td>
                          <td className="p-3.5 font-mono text-slate-300 text-[11px]">{strat.intervention_type}</td>
                          <td className="p-3.5 font-bold font-mono text-emerald-400">{strat.effectiveness_pct}%</td>
                          <td className="p-3.5 text-slate-400 text-xs max-w-xs">{strat.tradeoffs}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

