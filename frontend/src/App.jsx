import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Header from './components/Header';
import ScenarioSelector from './components/ScenarioSelector';
import NetworkTopology from './components/NetworkTopology';
import TelemetryCharts from './components/TelemetryCharts';
import AgentActivityPanel from './components/AgentActivityPanel';
import InterAgentMessageLog from './components/InterAgentMessageLog';
import RootCausePanel from './components/RootCausePanel';
import EvidenceCards from './components/EvidenceCards';
import DiagnosticHistory from './components/DiagnosticHistory';
import JsonReportModal from './components/JsonReportModal';
import ProtocolValidationTester from './components/ProtocolValidationTester';

import {
  fetchTopology,
  fetchScenarios,
  fetchScenarioTelemetry,
  runDiagnosis,
} from './api/client';

export default function App() {
  const [topology, setTopology] = useState({ nodes: [], edges: [] });
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState('link_congestion');
  const [telemetry, setTelemetry] = useState([]);
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [diagnosticResult, setDiagnosticResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [isProtocolTesterOpen, setIsProtocolTesterOpen] = useState(false);
  const [activeAgentId, setActiveAgentId] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Initial data loading
  useEffect(() => {
    async function init() {
      try {
        const [topoData, scData] = await Promise.all([
          fetchTopology(),
          fetchScenarios(),
        ]);
        setTopology(topoData);
        setScenarios(scData);

        // Load telemetry for default scenario
        const defaultTelem = await fetchScenarioTelemetry('link_congestion');
        setTelemetry(defaultTelem.telemetry || []);
      } catch (err) {
        console.error('Failed to initialize NOC dashboard:', err);
        setErrorMsg(`Failed to connect to backend engine: ${err.message}`);
      }
    }
    init();
  }, []);

  // Handle scenario selection
  const handleSelectScenario = async (scenarioId) => {
    setSelectedScenarioId(scenarioId);
    try {
      const data = await fetchScenarioTelemetry(scenarioId);
      setTelemetry(data.telemetry || []);
    } catch (err) {
      console.error(`Failed to load scenario telemetry:`, err);
    }
  };

  // Run Diagnosis Workflow
  const handleRunDiagnosis = async () => {
    try {
      setIsDiagnosing(true);
      setErrorMsg(null);

      // Call diagnosis endpoint
      const result = await runDiagnosis({ scenarioId: selectedScenarioId });

      // Animate simulated agent sequence with actual result data for visual polish
      const agents = ['perf-agent-01', 'infra-agent-01', 'conn-agent-01', 'corr-agent-01', 'recom-agent-01'];
      for (const ag of agents) {
        setActiveAgentId(ag);
        await new Promise((r) => setTimeout(r, 220));
      }
      setActiveAgentId(null);

      setDiagnosticResult(result);

      // Add to history
      setHistory((prev) => [
        {
          incident_id: result.incident_id,
          scenario_id: selectedScenarioId,
          status: result.status,
          suspected_root_cause: result.suspected_root_cause,
          confidence: result.confidence,
          execution_time_ms: result.execution_time_ms,
          timestamp: new Date().toLocaleTimeString(),
          full_result: result,
        },
        ...prev.slice(0, 7),
      ]);
    } catch (err) {
      console.error('Diagnosis error:', err);
      setErrorMsg(err.message || 'Diagnosis pipeline failed.');
    } finally {
      setIsDiagnosing(false);
    }
  };

  // Custom Raw CSV / JSON Submission
  const handleCustomSubmit = async ({ rawContent, dataFormat }) => {
    try {
      setIsDiagnosing(true);
      setErrorMsg(null);
      const result = await runDiagnosis({ rawContent, dataFormat });
      setDiagnosticResult(result);
      if (result.telemetry) {
        setTelemetry(result.telemetry);
      }
      setHistory((prev) => [
        {
          incident_id: result.incident_id,
          scenario_id: 'custom_upload',
          status: result.status,
          suspected_root_cause: result.suspected_root_cause,
          confidence: result.confidence,
          execution_time_ms: result.execution_time_ms,
          timestamp: new Date().toLocaleTimeString(),
          full_result: result,
        },
        ...prev.slice(0, 7),
      ]);
    } catch (err) {
      setErrorMsg(err.message || 'Custom telemetry parsing error');
    } finally {
      setIsDiagnosing(false);
    }
  };

  const handleSelectHistoryItem = (item) => {
    if (item.full_result) {
      setDiagnosticResult(item.full_result);
      if (item.scenario_id && item.scenario_id !== 'custom_upload') {
        setSelectedScenarioId(item.scenario_id);
        fetchScenarioTelemetry(item.scenario_id).then((d) => setTelemetry(d.telemetry || []));
      }
    }
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans">
      {/* Top NOC Header */}
      <Header
        status={diagnosticResult?.status}
        incidentId={diagnosticResult?.incident_id}
        isDiagnosing={isDiagnosing}
        onRunDiagnosis={handleRunDiagnosis}
        onOpenReport={() => setIsReportModalOpen(true)}
        onOpenProtocolTester={() => setIsProtocolTesterOpen(true)}
      />

      {/* Global Error Banner */}
      {errorMsg && (
        <div className="bg-rose-950/80 border-b border-rose-800 text-rose-200 px-6 py-2.5 text-xs font-mono flex items-center justify-between">
          <span>Error: {errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="underline hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Dashboard Grid */}
      <main className="flex-1 max-w-[1700px] w-full mx-auto px-4 sm:px-6 py-5 space-y-5">
        
        {/* Scenario Benchmark Selector */}
        <ScenarioSelector
          scenarios={scenarios}
          selectedScenarioId={selectedScenarioId}
          onSelectScenario={handleSelectScenario}
          onCustomTelemetrySubmit={handleCustomSubmit}
          isDiagnosing={isDiagnosing}
        />

        {/* Top Row: Network Topology + Telemetry Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-6">
            <NetworkTopology
              topology={topology}
              affectedDevices={diagnosticResult?.affected_devices || []}
            />
          </div>
          <div className="lg:col-span-6">
            <TelemetryCharts telemetry={telemetry} />
          </div>
        </div>

        {/* Multi-Agent Swarm Status Cards */}
        <AgentActivityPanel
          agentStates={diagnosticResult?.agent_states || []}
          activeAgentId={activeAgentId}
          isDiagnosing={isDiagnosing}
        />

        {/* Bottom Row: Root Cause Panel (Left) + Inter-Agent Message Log (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-6">
            <RootCausePanel report={diagnosticResult?.canonical_report} />
          </div>
          <div className="lg:col-span-6">
            <InterAgentMessageLog messages={diagnosticResult?.message_bus || []} />
          </div>
        </div>

        {/* Structured Evidence Ledger */}
        {diagnosticResult?.canonical_report?.supporting_evidence && (
          <EvidenceCards
            evidenceItems={diagnosticResult.canonical_report.supporting_evidence}
          />
        )}

        {/* Diagnostic Run Timeline */}
        <DiagnosticHistory
          history={history}
          onSelectHistoryItem={handleSelectHistoryItem}
          activeIncidentId={diagnosticResult?.incident_id}
        />

      </main>

      {/* Footer */}
      <footer className="border-t border-[#1f293d] bg-[#0c101b] py-3 px-6 text-center text-xs font-mono text-slate-500">
        IIT Bhubaneswar Agentic AI Grand Finale — NetCoop AI Autonomous Network Operations Center (NOC)
      </footer>

      {/* Modals */}
      <JsonReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        report={diagnosticResult?.canonical_report}
      />

      <ProtocolValidationTester
        isOpen={isProtocolTesterOpen}
        onClose={() => setIsProtocolTesterOpen(false)}
      />
    </div>
  );
}
