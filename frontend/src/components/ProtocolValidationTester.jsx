import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, X, Play, CheckCircle2, AlertOctagon, HelpCircle, Code } from 'lucide-react';
import { validateAgentMessage } from '../api/client';

export default function ProtocolValidationTester({ isOpen, onClose }) {
  const [testCase, setTestCase] = useState('valid');
  const [customJson, setCustomJson] = useState('');
  const [result, setResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);

  const sampleMessages = {
    valid: {
      agent_id: 'perf-agent-01',
      target_agent_id: 'corr-agent-01',
      message_type: 'TELEMETRY_ANOMALY',
      schema_version: '1.0.0',
      timestamp: new Date().toISOString(),
      device_id: 'Core-Router-01',
      metric: 'latency_ms',
      value: 142.5,
      unit: 'ms',
      evidence: { observed: 142.5, baseline: 5.0, severity: 'CRITICAL' },
      confidence: 0.94,
      findings: ['Latency exceeds 100ms critical threshold on Core-Router-01 egress trunk'],
      correlation_id: 'corr-8f12a9',
    },
    version_mismatch: {
      agent_id: 'legacy-probe-01',
      message_type: 'TELEMETRY_ANOMALY',
      schema_version: '0.8.2', // Legacy unsupported version!
      device_id: 'Agg-Switch-01',
      metric: 'packet_loss',
      value: 5.2,
      unit: '%',
    },
    missing_fields: {
      agent_id: 'fault-agent-02',
      // Missing message_type!
      // Missing schema_version!
      device_id: 'AP-01',
      metric: 'wifi_rssi_dbm',
      value: -85.0,
    },
    malformed_data: {
      agent_id: 'perf-agent-01',
      message_type: 'TELEMETRY_ANOMALY',
      schema_version: '1.0.0',
      device_id: 'Core-Router-01',
      confidence: 1.85, // Invalid: must be <= 1.0!
      metric: 'latency_ms',
      value: 'not_a_number',
    },
  };

  const handleSelectCase = (key) => {
    setTestCase(key);
    setCustomJson(JSON.stringify(sampleMessages[key], null, 2));
    setResult(null);
  };

  const handleValidate = async () => {
    try {
      setIsValidating(true);
      const parsed = JSON.parse(customJson || JSON.stringify(sampleMessages.valid));
      const res = await validateAgentMessage(parsed);
      setResult(res);
    } catch (err) {
      setResult({
        valid: false,
        error_type: 'JSON_SYNTAX_ERROR',
        error_detail: `JSON syntax error: ${err.message}`,
      });
    } finally {
      setIsValidating(false);
    }
  };

  // Initialize with valid case
  React.useEffect(() => {
    if (!customJson) {
      setCustomJson(JSON.stringify(sampleMessages.valid, null, 2));
    }
  }, []);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="w-full max-w-3xl max-h-[90vh] bg-[#0c101c] border border-[#22314d] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f2c45] bg-[#0f1422]">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-cyan-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Canonical Protocol Interoperability Inspector</h3>
                <p className="text-xs text-slate-400 font-mono">
                  Real-Time Pydantic Schema Validation & Mismatch Detection
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#1f2c45] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-5 overflow-auto space-y-4">
            {/* Quick Test Case Buttons */}
            <div>
              <div className="text-xs font-mono text-slate-400 mb-2">Preset Test Payloads:</div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <button
                  onClick={() => handleSelectCase('valid')}
                  className={`p-2 rounded-lg border text-left transition-all ${
                    testCase === 'valid'
                      ? 'bg-emerald-950/40 border-emerald-400 text-emerald-300'
                      : 'bg-[#0a0d16] border-[#1b253b] text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Valid Message
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Complies with v1.0.0</div>
                </button>

                <button
                  onClick={() => handleSelectCase('version_mismatch')}
                  className={`p-2 rounded-lg border text-left transition-all ${
                    testCase === 'version_mismatch'
                      ? 'bg-rose-950/40 border-rose-400 text-rose-300'
                      : 'bg-[#0a0d16] border-[#1b253b] text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="font-bold flex items-center gap-1">
                    <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />
                    Version Mismatch
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Legacy v0.8.2 schema</div>
                </button>

                <button
                  onClick={() => handleSelectCase('missing_fields')}
                  className={`p-2 rounded-lg border text-left transition-all ${
                    testCase === 'missing_fields'
                      ? 'bg-amber-950/40 border-amber-400 text-amber-300'
                      : 'bg-[#0a0d16] border-[#1b253b] text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="font-bold flex items-center gap-1">
                    <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
                    Missing Fields
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Omitted message_type</div>
                </button>

                <button
                  onClick={() => handleSelectCase('malformed_data')}
                  className={`p-2 rounded-lg border text-left transition-all ${
                    testCase === 'malformed_data'
                      ? 'bg-purple-950/40 border-purple-400 text-purple-300'
                      : 'bg-[#0a0d16] border-[#1b253b] text-slate-400 hover:text-white'
                  }`}
                >
                  <div className="font-bold flex items-center gap-1">
                    <Code className="w-3.5 h-3.5 text-purple-400" />
                    Malformed Data
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Confidence out of bounds</div>
                </button>
              </div>
            </div>

            {/* Editable JSON Box */}
            <div>
              <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1.5">
                <span>AgentMessage JSON Payload (Editable):</span>
                <span>Enforced by Pydantic Model</span>
              </div>
              <textarea
                value={customJson}
                onChange={(e) => setCustomJson(e.target.value)}
                rows={9}
                className="w-full bg-[#07090f] border border-[#1b253b] focus:border-cyan-500 rounded-xl p-3 font-mono text-xs text-slate-200 outline-none resize-none"
              />
            </div>

            {/* Validate Button */}
            <div className="flex justify-end">
              <button
                disabled={isValidating}
                onClick={handleValidate}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs shadow-md shadow-cyan-500/20 cursor-pointer disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-black" />
                <span>Validate Against Canonical Protocol</span>
              </button>
            </div>

            {/* Live Result Display */}
            {result && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-4 rounded-xl border font-mono text-xs ${
                  result.valid
                    ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                    : 'bg-rose-950/20 border-rose-500/40 text-rose-300'
                }`}
              >
                <div className="flex items-center gap-2 font-bold mb-1.5">
                  {result.valid ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span>VALID PROTOCOL MESSAGE (Accepted)</span>
                    </>
                  ) : (
                    <>
                      <AlertOctagon className="w-4 h-4 text-rose-400" />
                      <span>PROTOCOL REJECTION ({result.error_type})</span>
                    </>
                  )}
                </div>

                <div className="text-slate-300 leading-relaxed text-[11px]">
                  {result.valid ? result.message : result.error_detail}
                </div>

                {result.supported_versions && (
                  <div className="mt-2 pt-2 border-t border-[#24354f] text-[10px] text-slate-400">
                    Supported Schema Versions: {result.supported_versions.join(', ')}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
