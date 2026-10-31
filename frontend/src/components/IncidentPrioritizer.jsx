import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { fetchIncidentPrioritization } from '../api/client';

export default function IncidentPrioritizer({ onSimulateIncident }) {
  const [incidents, setIncidents] = useState([]);
  const [filterSeverity, setFilterSeverity] = useState('ALL'); // 'ALL' | 'CRITICAL' | 'WARNING'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadIncidents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchIncidentPrioritization();
      setIncidents(data);
    } catch (err) {
      setError(err.message || 'Failed to load incident prioritization list');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  const filteredIncidents = incidents.filter((inc) => {
    if (filterSeverity === 'ALL') return true;
    return inc.severity === filterSeverity;
  });

  const getPriorityBadge = (priority) => {
    if (priority === 'P1') {
      return <span className="px-2.5 py-1 rounded text-xs font-black bg-rose-600 text-white shadow-md shadow-rose-900/40">P1 CRITICAL</span>;
    }
    if (priority === 'P2') {
      return <span className="px-2.5 py-1 rounded text-xs font-bold bg-amber-500 text-slate-950">P2 HIGH</span>;
    }
    if (priority === 'P3') {
      return <span className="px-2.5 py-1 rounded text-xs font-bold bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">P3 MEDIUM</span>;
    }
    return <span className="px-2.5 py-1 rounded text-xs font-semibold bg-slate-700 text-slate-300">P4 LOW</span>;
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-rose-500/20 text-rose-400 border border-rose-500/30">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </span>
            <h2 className="text-lg font-bold text-slate-100">Multi-Incident Operational Prioritization</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Algorithmic incident triage ranking detected network anomalies by severity, blast radius, SLA violation, and propagation potential.
          </p>
        </div>

        {/* Severity Filter Controls */}
        <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
          {['ALL', 'CRITICAL', 'WARNING'].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                filterSeverity === sev ? 'bg-slate-800 text-cyan-300 shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {sev}
            </button>
          ))}
          <button
            onClick={loadIncidents}
            disabled={loading}
            className="p-1.5 text-slate-400 hover:text-slate-200 transition-all ml-1"
            title="Refresh Prioritization Queue"
          >
            🔄
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs">
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-2">
          <div className="w-6 h-6 border-2 border-rose-400 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs">Computing deterministic incident prioritization matrix...</span>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredIncidents.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No incidents match the active filter criteria.
            </div>
          ) : (
            filteredIncidents.map((inc, idx) => {
              const isP1 = inc.priority === 'P1';
              return (
                <motion.div
                  key={inc.incident_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className={`p-4 rounded-xl border transition-all ${
                    isP1
                      ? 'bg-rose-950/20 border-rose-500/50 shadow-lg shadow-rose-900/10'
                      : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800/80 pb-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        {getPriorityBadge(inc.priority)}
                        <span className="text-xs font-mono font-bold text-slate-400">#{inc.incident_id}</span>
                        <span className="text-xs font-mono text-cyan-400 font-semibold">[{inc.device_id}]</span>
                        {inc.sla_breached && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                            SLA BREACHED
                          </span>
                        )}
                      </div>
                      <h3 className="text-sm font-bold text-slate-100">{inc.title}</h3>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <span className="text-[10px] font-mono text-slate-500 uppercase block">Priority Score</span>
                        <span className={`text-lg font-black font-mono ${
                          inc.priority_score >= 80 ? 'text-rose-400' : 'text-amber-400'
                        }`}>
                          {inc.priority_score} <span className="text-xs font-normal text-slate-500">/ 100</span>
                        </span>
                      </div>

                      {onSimulateIncident && (
                        <button
                          onClick={() => onSimulateIncident(inc)}
                          className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs rounded-lg transition-all shadow shadow-cyan-900/30 flex items-center gap-1.5"
                        >
                          <span>🔬</span>
                          <span>Simulate</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Impact & Propagation Details */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 py-3 text-xs border-b border-slate-800/80">
                    <div>
                      <span className="text-slate-500 text-[10px] font-mono uppercase block">Suspected Root Cause</span>
                      <span className="text-slate-200 font-semibold">{inc.suspected_root_cause}</span>
                    </div>

                    <div>
                      <span className="text-slate-500 text-[10px] font-mono uppercase block">Downstream Blast Radius</span>
                      <span className="text-slate-300">
                        {inc.affected_devices_count} device(s) ({inc.affected_devices.join(', ')})
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-500 text-[10px] font-mono uppercase block">Propagation Risk</span>
                      <span className={`font-mono font-bold ${
                        inc.propagation_risk === 'HIGH' ? 'text-rose-400' : 'text-amber-400'
                      }`}>
                        {inc.propagation_risk}
                      </span>
                    </div>
                  </div>

                  {/* Service Impact & Recommended Action */}
                  <div className="pt-3 flex flex-wrap items-center justify-between gap-3 text-xs">
                    <div className="text-slate-400 max-w-xl">
                      <span className="font-semibold text-slate-300">Operational Impact: </span>
                      {inc.service_impact}
                    </div>

                    <div className="text-cyan-300 font-mono text-[11px] bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
                      <span className="text-slate-500 uppercase mr-1">Recommended:</span>
                      {inc.recommended_action}
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

