import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Header from './components/Header';
import ScenarioSelector from './components/ScenarioSelector';
import InvestigationReplay from './components/InvestigationReplay';
import NetworkTopology from './components/NetworkTopology';
import TelemetryCharts from './components/TelemetryCharts';
import AgentActivityPanel from './components/AgentActivityPanel';
import InterAgentMessageLog from './components/InterAgentMessageLog';
import RootCausePanel from './components/RootCausePanel';
import EvidenceCards from './components/EvidenceCards';
import DiagnosticHistory from './components/DiagnosticHistory';
import JsonReportModal from './components/JsonReportModal';
import ProtocolValidationTester from './components/ProtocolValidationTester';
import DeviceDetailsModal from './components/DeviceDetailsModal';
import WhatIfSimulator from './components/WhatIfSimulator';
import DigitalTwinView from './components/DigitalTwinView';
import IncidentPrioritizer from './components/IncidentPrioritizer';
import FaultInjectionStudio from './components/FaultInjectionStudio';
import CommandCenterView from './components/CommandCenterView';
import NetworkIntegrationsView from './components/NetworkIntegrationsView';
import TelemetryGeneratorView from './components/TelemetryGeneratorView';

import {
  fetchTopology,
  fetchScenarios,
  fetchScenarioTelemetry,
  fetchInvestigations,
  fetchInvestigationById,
  runDiagnosis,
} from './api/client';

export default function App() {
  const [topology, setTopology] = useState({ nodes: [], edges: [] });
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState('conflicting_evidence');
  const [telemetry, setTelemetry] = useState([]);
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [diagnosticResult, setDiagnosticResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [isProtocolTesterOpen, setIsProtocolTesterOpen] = useState(false);
  const [selectedDeviceNode, setSelectedDeviceNode] = useState(null);
  const [isDeviceModalOpen, setIsDeviceModalOpen] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Top-Level Navigation View: 'ops' | 'digital_twin' | 'what_if' | 'prioritizer' | 'fault_injection'
  const [activeView, setActiveView] = useState('ops');

  // Investigation Replay State
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlayingReplay, setIsPlayingReplay] = useState(false);
  const [replaySpeed, setReplaySpeed] = useState(1);
  const [pastInvestigations, setPastInvestigations] = useState([]);

  // Initial data loading
  useEffect(() => {
    async function init() {
      try {
        const [topoData, scData, pastInvList] = await Promise.all([
          fetchTopology(),
          fetchScenarios(),
          fetchInvestigations().catch(() => []),
        ]);
        setTopology(topoData);
        setScenarios(scData);
        setPastInvestigations(pastInvList);

        // Load telemetry for default showstopper scenario: Scenario 8 (conflicting_evidence)
        const defaultTelem = await fetchScenarioTelemetry('conflicting_evidence');
        setTelemetry(defaultTelem.telemetry || []);

        // If past investigations exist, pre-populate with the latest
        if (pastInvList.length > 0) {
          const latest = await fetchInvestigationById(pastInvList[0].incident_id);
          setDiagnosticResult(latest);
          if (latest.telemetry) setTelemetry(latest.telemetry);
          const evts = latest.timeline_events || [];
          setTimelineEvents(evts);
          setCurrentStepIndex(evts.length > 0 ? evts.length - 1 : 0);
        }
      } catch (err) {
        console.error('Failed to initialize NOC dashboard:', err);
        setErrorMsg(`Failed to connect to backend engine: ${err.message}`);
      }
    }
    init();
  }, []);

  // Timer loop for replay stepping
  useEffect(() => {
    if (!isPlayingReplay || timelineEvents.length === 0) return;
    const intervalTime = Math.max(250, Math.round(1200 / replaySpeed));
    const timer = setInterval(() => {
      setCurrentStepIndex((prev) => {
        if (prev >= timelineEvents.length - 1) {
          setIsPlayingReplay(false);
          return prev;
        }
        return prev + 1;
      });
    }, intervalTime);
    return () => clearInterval(timer);
  }, [isPlayingReplay, timelineEvents.length, replaySpeed]);

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
      setIsPlayingReplay(false);

      // Call diagnosis endpoint
      const result = await runDiagnosis({ scenarioId: selectedScenarioId });
      setDiagnosticResult(result);
      if (result.telemetry) {
        setTelemetry(result.telemetry);
      }

      const evts = result.timeline_events || [];
      setTimelineEvents(evts);
      setCurrentStepIndex(0);
      setIsPlayingReplay(true); // Automatically play replay of newly executed investigation!

      // Refresh past investigations list
      fetchInvestigations().then(setPastInvestigations).catch(() => {});

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

  // Load Past Investigation for Replay
  const handleSelectPastInvestigation = async (incId) => {
    try {
      const inv = await fetchInvestigationById(incId);
      setDiagnosticResult(inv);
      if (inv.telemetry) setTelemetry(inv.telemetry);
      const evts = inv.timeline_events || [];
      setTimelineEvents(evts);
      setCurrentStepIndex(0);
      setIsPlayingReplay(true);
    } catch (err) {
      setErrorMsg(`Failed to load investigation #${incId}: ${err.message}`);
    }
  };

  const handleSelectLiveInvestigation = async (incId) => {
    await handleSelectPastInvestigation(incId);
    setActiveView('ops');
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
      const evts = result.timeline_events || [];
      setTimelineEvents(evts);
      setCurrentStepIndex(0);
      setIsPlayingReplay(true);

      fetchInvestigations().then(setPastInvestigations).catch(() => {});

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
      if (item.full_result.telemetry) {
        setTelemetry(item.full_result.telemetry);
      }
      const evts = item.full_result.timeline_events || [];
      setTimelineEvents(evts);
      setCurrentStepIndex(evts.length > 0 ? evts.length - 1 : 0);
    }
  };

  const handleDeviceClick = (node) => {
    setSelectedDeviceNode(node);
    setIsDeviceModalOpen(true);
  };

  // Active step details
  const currentEvent = timelineEvents.length > 0 ? timelineEvents[currentStepIndex] : null;
  const activeAgentId = currentEvent?.agent_id || null;
  const activeCommunicatingNode = currentEvent?.device_id || null;
  const effectiveAffectedDevices = (currentEvent?.affected_devices && currentEvent.affected_devices.length > 0)
    ? currentEvent.affected_devices
    : (diagnosticResult?.affected_devices || []);

  const currentTelemetryOrigin =
    diagnosticResult?.canonical_report?.telemetry_origin ||
    diagnosticResult?.telemetry_origin ||
    'SIMULATED';

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans">
      {/* Top NOC Header */}
      <Header
        status={diagnosticResult?.status}
        incidentId={diagnosticResult?.incident_id}
        telemetryOrigin={currentTelemetryOrigin}
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
        
        {/* Top-Level Navigation View Switcher */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0d121f] p-2 rounded-xl border border-[#1f293d] shadow-lg">
          <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
            <button
              onClick={() => setActiveView('command_center')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
                activeView === 'command_center'
                  ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-900/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <span>🌟</span>
              <span>NOC Command Center</span>
            </button>

            <button
              onClick={() => setActiveView('integrations')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
                activeView === 'integrations'
                  ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-900/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <span>🔌</span>
              <span>Live Integrations</span>
            </button>

            <button
              onClick={() => setActiveView('ops')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
                activeView === 'ops'
                  ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md shadow-cyan-900/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <span>🧭</span>
              <span>NOC Operations & Replay</span>
            </button>

            <button
              onClick={() => setActiveView('digital_twin')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
                activeView === 'digital_twin'
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md shadow-indigo-900/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <span>🌐</span>
              <span>Network Digital Twin</span>
            </button>

            <button
              onClick={() => setActiveView('what_if')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
                activeView === 'what_if'
                  ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-900/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <span>🔬</span>
              <span>What-If Remediation Simulator</span>
            </button>

            <button
              onClick={() => setActiveView('prioritizer')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
                activeView === 'prioritizer'
                  ? 'bg-gradient-to-r from-rose-600 to-amber-600 text-white shadow-md shadow-rose-900/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <span>🚨</span>
              <span>Incident Prioritization</span>
            </button>

            <button
              onClick={() => setActiveView('fault_injection')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
                activeView === 'fault_injection'
                  ? 'bg-gradient-to-r from-amber-600 to-orange-600 text-white shadow-md shadow-amber-900/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <span>⚡</span>
              <span>Fault Injection Studio</span>
            </button>

            <button
              onClick={() => setActiveView('generator')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all ${
                activeView === 'generator'
                  ? 'bg-gradient-to-r from-amber-500 to-yellow-500 text-slate-950 font-bold shadow-md shadow-amber-900/30'
                  : 'text-amber-400/90 hover:text-amber-300 hover:bg-slate-800/60'
              }`}
            >
              <span>🧪</span>
              <span>Official Telemetry Benchmark</span>
            </button>
          </div>

          <div className="hidden xl:flex items-center gap-2 text-xs font-mono text-slate-400 pr-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            <span>Mode: {activeView.toUpperCase().replace(/_/g, ' ')}</span>
          </div>
        </div>

        {/* VIEW 0: Autonomous NOC Command Center */}
        {activeView === 'command_center' && (
          <CommandCenterView onNavigateToReplay={() => setActiveView('ops')} />
        )}

        {/* VIEW 0.5: Live Network Integrations & Telemetry Adapters */}
        {activeView === 'integrations' && (
          <NetworkIntegrationsView
            onSelectLiveInvestigation={handleSelectLiveInvestigation}
            currentTelemetryOrigin={currentTelemetryOrigin}
          />
        )}

        {/* VIEW 1: Primary NOC Operations & Replay View */}
        {activeView === 'ops' && (
          <div className="space-y-5">
            {/* Scenario Benchmark Selector */}
            <ScenarioSelector
              scenarios={scenarios}
              selectedScenarioId={selectedScenarioId}
              onSelectScenario={handleSelectScenario}
              onCustomTelemetrySubmit={handleCustomSubmit}
              isDiagnosing={isDiagnosing}
            />

            {/* Autonomous Investigation Replay Bar */}
            {timelineEvents.length > 0 && (
              <InvestigationReplay
                timelineEvents={timelineEvents}
                currentStepIndex={currentStepIndex}
                onStepChange={(idx) => {
                  setCurrentStepIndex(idx);
                  setIsPlayingReplay(false);
                }}
                isPlaying={isPlayingReplay}
                onTogglePlay={() => setIsPlayingReplay(!isPlayingReplay)}
                speed={replaySpeed}
                onSpeedChange={setReplaySpeed}
                pastInvestigations={pastInvestigations}
                onSelectPastInvestigation={handleSelectPastInvestigation}
                activeIncidentId={diagnosticResult?.incident_id}
              />
            )}

            {/* Top Row: Network Topology + Telemetry Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              <div className="lg:col-span-6">
                <NetworkTopology
                  topology={topology}
                  affectedDevices={effectiveAffectedDevices}
                  faultPropagationPaths={diagnosticResult?.fault_propagation_paths || []}
                  activeCommunicatingNode={activeCommunicatingNode}
                  activeAgentId={activeAgentId}
                  onSelectDevice={handleDeviceClick}
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
          </div>
        )}

        {/* VIEW 2: Network Digital Twin */}
        {activeView === 'digital_twin' && (
          <DigitalTwinView onSelectDevice={handleDeviceClick} />
        )}

        {/* VIEW 3: What-If Remediation Simulator & Strategy Comparison */}
        {activeView === 'what_if' && (
          <WhatIfSimulator
            diagnosticResult={diagnosticResult}
            onSimulationApplied={(simResult) => {
              // Optionally log or sync simulation result
            }}
          />
        )}

        {/* VIEW 4: Multi-Incident Operational Prioritization */}
        {activeView === 'prioritizer' && (
          <IncidentPrioritizer
            onSimulateIncident={(inc) => {
              setActiveView('what_if');
            }}
          />
        )}

        {/* VIEW 5: Interactive Fault Injection Studio */}
        {activeView === 'fault_injection' && (
          <FaultInjectionStudio
            onDiagnosisComplete={(res) => {
              setDiagnosticResult(res);
              if (res.telemetry) setTelemetry(res.telemetry);
              const evts = res.timeline_events || [];
              setTimelineEvents(evts);
              setCurrentStepIndex(0);
              setIsPlayingReplay(true);
              setActiveView('ops');
            }}
          />
        )}

        {/* VIEW 6: Official Problem-Statement Telemetry Generator */}
        {activeView === 'generator' && (
          <TelemetryGeneratorView
            onSelectInvestigation={(res) => {
              setDiagnosticResult(res);
              if (res.telemetry) setTelemetry(res.telemetry);
              const evts = res.timeline_events || [];
              setTimelineEvents(evts);
              setCurrentStepIndex(0);
              setIsPlayingReplay(true);
              setActiveView('ops');
            }}
            onNavigateToOps={() => setActiveView('ops')}
          />
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-[#1f293d] bg-[#0c101b] py-3 px-6 text-center text-xs font-mono text-slate-500">
        IIT Bhubaneswar Agentic AI Grand Finale — NetCoop AI Autonomous Network Operations Center (NOC)
      </footer>

      {/* Modals & Drawers */}
      <JsonReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        report={diagnosticResult?.canonical_report}
      />

      <ProtocolValidationTester
        isOpen={isProtocolTesterOpen}
        onClose={() => setIsProtocolTesterOpen(false)}
      />

      <DeviceDetailsModal
        isOpen={isDeviceModalOpen}
        onClose={() => setIsDeviceModalOpen(false)}
        deviceNode={selectedDeviceNode}
        telemetryRecord={telemetry.find((t) => t.device_id === selectedDeviceNode?.id)}
        isImplicated={effectiveAffectedDevices.includes(selectedDeviceNode?.id)}
      />
    </div>
  );
}
