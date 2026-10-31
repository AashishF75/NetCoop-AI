import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  generateOfficialTelemetry,
  validateOfficialTelemetry,
  diagnoseOfficialTelemetry,
} from '../api/client';
import {
  Zap,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Activity,
  Cpu,
  Layers,
  ArrowRight,
  ShieldCheck,
  Code2,
  Sliders,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

const FAULT_OPTIONS = [
  {
    id: 'normal',
    name: 'Normal Network',
    badge: 'HEALTHY',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    description: 'Baseline campus operation. CPU 10-35%, link util 20-50%, latency 5-20ms, 0% loss, 0 queue drops.',
    icon: CheckCircle2,
    iconColor: 'text-emerald-400',
  },
  {
    id: 'latency_spike',
    name: 'Latency Spike',
    badge: 'WARNING',
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    description: 'Transit latency explosion (150-400ms) & jitter (30-80ms) with moderate CPU (40-70%) and minor packet loss.',
    icon: AlertTriangle,
    iconColor: 'text-amber-400',
  },
  {
    id: 'hardware_failure',
    name: 'Hardware Failure',
    badge: 'CRITICAL',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    description: 'Severe switch route processor crash. CPU 99.9%, link 100%, 15-30% loss, 5k-15k queue drops, 100-500 CRC errors.',
    icon: XCircle,
    iconColor: 'text-rose-400',
  },
];

export default function TelemetryGeneratorView({ onSelectInvestigation, onNavigateToOps }) {
  const [selectedFault, setSelectedFault] = useState('latency_spike');
  const [generatedPayload, setGeneratedPayload] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [diagnosisResult, setDiagnosisResult] = useState(null);
  const [validationStatus, setValidationStatus] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [jsonTab, setJsonTab] = useState('raw'); // 'raw' | 'parsed'

  // Generate fresh telemetry
  const handleGenerate = async (faultTypeToUse = selectedFault) => {
    setIsGenerating(true);
    setErrorMsg(null);
    setDiagnosisResult(null);
    setValidationStatus(null);
    try {
      const resp = await generateOfficialTelemetry(faultTypeToUse);
      setGeneratedPayload(resp.raw_telemetry);
      
      // Auto-validate schema
      try {
        await validateOfficialTelemetry(resp.raw_telemetry);
        setValidationStatus({ valid: true, message: 'Official schema compliant' });
      } catch (valErr) {
        setValidationStatus({ valid: false, message: valErr.message });
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to generate telemetry');
    } finally {
      setIsGenerating(false);
    }
  };

  // Submit to 5-agent diagnosis pipeline
  const handleDiagnose = async () => {
    if (!generatedPayload) return;
    setIsDiagnosing(true);
    setErrorMsg(null);
    try {
      const resp = await diagnoseOfficialTelemetry({
        faultType: selectedFault,
        rawTelemetry: generatedPayload,
      });
      setDiagnosisResult(resp);
      if (onSelectInvestigation && resp.full_result) {
        onSelectInvestigation(resp.full_result);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Diagnosis failed on generated telemetry');
    } finally {
      setIsDiagnosing(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'CONFIRMED':
        return <span className="px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs font-bold font-mono">CONFIRMED</span>;
      case 'SUSPECTED':
        return <span className="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-bold font-mono">SUSPECTED</span>;
      case 'HEALTHY':
        return <span className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-bold font-mono">HEALTHY</span>;
      case 'INCONCLUSIVE':
        return <span className="px-2.5 py-1 rounded bg-purple-500/20 text-purple-300 border border-purple-500/40 text-xs font-bold font-mono">INCONCLUSIVE</span>;
      default:
        return <span className="px-2.5 py-1 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 text-xs font-bold font-mono">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Disclaimer */}
      <div className="bg-gradient-to-r from-amber-950/40 via-yellow-950/20 to-slate-900 border border-amber-700/40 rounded-xl p-5 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-100">
                  Official Problem-Statement Telemetry Generator & Multi-Agent Test Bench
                </h2>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase bg-yellow-500/20 text-yellow-300 border border-yellow-500/50">
                  GENERATED_TEST
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Integrates the official benchmark generator (<code className="text-amber-300">generate_telemetry(fault_type)</code>) and tests the 5-agent reasoning pipeline across Healthy, Warning, and Critical states.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              Source Provenance: <strong className="text-yellow-400">GENERATED_TEST</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {errorMsg && (
        <div className="bg-rose-950/80 border border-rose-800 text-rose-200 px-4 py-3 rounded-xl text-xs font-mono flex items-center justify-between">
          <span>Error: {errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="underline hover:text-white">Dismiss</button>
        </div>
      )}

      {/* Step 1: Select Fault Type */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {FAULT_OPTIONS.map((opt) => {
          const isSelected = selectedFault === opt.id;
          const Icon = opt.icon;
          return (
            <motion.div
              key={opt.id}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={() => {
                setSelectedFault(opt.id);
                handleGenerate(opt.id);
              }}
              className={`cursor-pointer rounded-xl p-4 border transition-all ${
                isSelected
                  ? 'bg-[#121829] border-cyan-500/80 shadow-lg shadow-cyan-950/40 ring-1 ring-cyan-500/40'
                  : 'bg-[#0d121f] border-[#1f293d] hover:border-slate-700 text-slate-400'
              }`}
            >
              <div className="flex items-center justify-between mb-2.5">
                <div className="flex items-center gap-2">
                  <Icon className={`w-4 h-4 ${opt.iconColor}`} />
                  <span className={`font-bold text-sm ${isSelected ? 'text-white' : 'text-slate-200'}`}>
                    {opt.name}
                  </span>
                </div>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${opt.badgeColor}`}>
                  {opt.badge}
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed font-sans">{opt.description}</p>
            </motion.div>
          );
        })}
      </div>

      {/* Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0d121f] p-3.5 rounded-xl border border-[#1f293d]">
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleGenerate()}
            disabled={isGenerating}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-all disabled:opacity-50"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
            <span>Generate New Sample ({selectedFault})</span>
          </button>

          {validationStatus && (
            <div className="flex items-center gap-1.5 text-xs font-mono">
              {validationStatus.valid ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Schema Valid
                </span>
              ) : (
                <span className="text-rose-400 flex items-center gap-1">
                  <XCircle className="w-3.5 h-3.5" /> {validationStatus.message}
                </span>
              )}
            </div>
          )}
        </div>

        <button
          onClick={handleDiagnose}
          disabled={!generatedPayload || isDiagnosing}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-md shadow-cyan-900/30 transition-all disabled:opacity-40"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>{isDiagnosing ? 'Agents Cross-Examining...' : 'Submit to 5-Agent Diagnosis'}</span>
        </button>
      </div>

      {/* Main Dual View: Raw Telemetry + Diagnosis Result */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Left: Generated Problem-Statement Telemetry */}
        <div className="bg-[#0d121f] border border-[#1f293d] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Code2 className="w-4 h-4 text-cyan-400" />
              <h3 className="font-bold text-sm text-slate-100">
                Official Generated Telemetry Payload
              </h3>
            </div>
            {generatedPayload && (
              <span className="text-xs font-mono text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
                {generatedPayload.device_id}
              </span>
            )}
          </div>

          {generatedPayload ? (
            <div className="space-y-3 font-mono text-xs">
              {/* Metric KPI Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
                <div className="bg-slate-900/70 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">CPU Utilization</span>
                  <strong className={generatedPayload.metrics?.cpu_utilization_pct >= 90 ? 'text-rose-400' : 'text-slate-100'}>
                    {generatedPayload.metrics?.cpu_utilization_pct}%
                  </strong>
                </div>
                <div className="bg-slate-900/70 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Link Utilization</span>
                  <strong className={generatedPayload.metrics?.link_utilization_pct >= 90 ? 'text-rose-400' : 'text-slate-100'}>
                    {generatedPayload.metrics?.link_utilization_pct}%
                  </strong>
                </div>
                <div className="bg-slate-900/70 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Packet Loss</span>
                  <strong className={generatedPayload.metrics?.packet_loss_pct > 1 ? 'text-rose-400' : 'text-slate-100'}>
                    {generatedPayload.metrics?.packet_loss_pct}%
                  </strong>
                </div>
                <div className="bg-slate-900/70 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Transit Latency</span>
                  <strong className={generatedPayload.metrics?.latency_ms >= 100 ? 'text-amber-400' : 'text-slate-100'}>
                    {generatedPayload.metrics?.latency_ms} ms
                  </strong>
                </div>
                <div className="bg-slate-900/70 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Jitter</span>
                  <span className="text-slate-100 font-bold">
                    {generatedPayload.metrics?.jitter_ms !== undefined ? `${generatedPayload.metrics.jitter_ms} ms` : 'N/A'}
                  </span>
                </div>
                <div className="bg-slate-900/70 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Queue Drops</span>
                  <strong className={generatedPayload.metrics?.queue_drops > 100 ? 'text-rose-400' : 'text-slate-100'}>
                    {generatedPayload.metrics?.queue_drops}
                  </strong>
                </div>
                {generatedPayload.metrics?.interface_errors !== undefined && (
                  <div className="bg-slate-900/70 p-2.5 rounded border border-slate-800 col-span-2 sm:col-span-3">
                    <span className="text-slate-400 block text-[10px]">Interface CRC Errors</span>
                    <strong className="text-rose-400">
                      {generatedPayload.metrics.interface_errors} errors/sec
                    </strong>
                  </div>
                )}
              </div>

              {/* Exact JSON View */}
              <div className="relative">
                <pre className="p-3 bg-[#07090e] border border-slate-800 rounded-lg overflow-x-auto text-[11px] text-cyan-300/90 leading-tight max-h-[300px]">
                  {JSON.stringify(generatedPayload, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="py-16 text-center text-slate-500 font-mono text-xs">
              Click &quot;Generate New Sample&quot; to produce official problem-statement telemetry.
            </div>
          )}
        </div>

        {/* Right: Multi-Agent Diagnosis Result */}
        <div className="bg-[#0d121f] border border-[#1f293d] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h3 className="font-bold text-sm text-slate-100">
                Multi-Agent Autonomous Diagnosis
              </h3>
            </div>
            {diagnosisResult && (
              <span className="text-xs font-mono text-yellow-300 bg-yellow-950/60 px-2 py-0.5 rounded border border-yellow-800">
                PROVENANCE: {diagnosisResult.telemetry_origin}
              </span>
            )}
          </div>

          {diagnosisResult ? (
            <div className="space-y-4">
              {/* Diagnosis Header Card */}
              <div className="bg-[#121829] border border-slate-700/60 rounded-xl p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {getStatusBadge(diagnosisResult.status)}
                    <span className="text-xs font-mono text-slate-400">
                      Incident: <strong className="text-slate-200">{diagnosisResult.incident_id}</strong>
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs font-mono">
                    <span className="text-slate-400">Confidence:</span>
                    <strong className="text-cyan-300">
                      {diagnosisResult.confidence ? `${Math.round(diagnosisResult.confidence * 100)}%` : '100%'}
                    </strong>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Suspected Root Cause</span>
                  <h4 className="text-base font-bold text-white mt-0.5">
                    {diagnosisResult.suspected_root_cause}
                  </h4>
                </div>

                <div className="flex flex-wrap gap-1.5 text-[11px] font-mono">
                  <span className="text-slate-400">Affected Node:</span>
                  <span className="text-cyan-300 bg-slate-800 px-2 py-0.5 rounded">
                    {diagnosisResult.affected_devices?.join(', ') || 'None'}
                  </span>
                </div>
              </div>

              {/* Competing Hypotheses Evaluated */}
              {diagnosisResult.competing_hypotheses?.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs font-bold text-slate-300 font-mono flex items-center gap-1.5">
                    <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                    Competing Hypotheses Evaluated by Swarm:
                  </span>
                  <div className="space-y-1.5">
                    {diagnosisResult.competing_hypotheses.slice(0, 3).map((hyp, idx) => (
                      <div
                        key={hyp.hypothesis_id || idx}
                        className={`p-2.5 rounded-lg border text-xs font-mono flex items-center justify-between ${
                          hyp.status === 'VALIDATED'
                            ? 'bg-emerald-950/20 border-emerald-800/60 text-emerald-300'
                            : 'bg-slate-900/60 border-slate-800 text-slate-400'
                        }`}
                      >
                        <div className="truncate pr-2">
                          <strong className="text-slate-200">{hyp.name}</strong>
                          <span className="block text-[10px] text-slate-400 truncate">{hyp.reasoning || hyp.description}</span>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <span className="font-bold">{Math.round((hyp.probability || 0) * 100)}%</span>
                          <span className={`block text-[9px] font-semibold uppercase ${hyp.status === 'VALIDATED' ? 'text-emerald-400' : 'text-slate-500'}`}>
                            {hyp.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommended Playbook */}
              {((diagnosisResult.report?.recommended_actions && diagnosisResult.report.recommended_actions.length > 0) ||
                (diagnosisResult.report?.remediation_plan?.steps && diagnosisResult.report.remediation_plan.steps.length > 0)) && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3 space-y-2">
                  <span className="text-xs font-bold text-slate-300 font-mono flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                    Recommended Remediation Actions:
                  </span>
                  <ul className="space-y-1 text-xs text-slate-300 font-sans list-disc list-inside">
                    {(diagnosisResult.report.recommended_actions || diagnosisResult.report.remediation_plan.steps).slice(0, 3).map((step, sIdx) => (
                      <li key={sIdx} className="leading-relaxed">
                        <strong className="text-slate-200">{step.action}:</strong> {step.rationale || step.description || step.command}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Button to View in Ops / Replay */}
              {onNavigateToOps && (
                <button
                  onClick={onNavigateToOps}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-cyan-300 text-xs font-bold transition-all"
                >
                  <span>Inspect Full Inter-Agent Replay in Operations Center</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ) : (
            <div className="py-16 text-center text-slate-500 font-mono text-xs">
              {isDiagnosing
                ? '5 Specialized agents are analyzing metrics and negotiating hypotheses...'
                : 'Click "Submit to 5-Agent Diagnosis" to run multi-agent evaluation.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
