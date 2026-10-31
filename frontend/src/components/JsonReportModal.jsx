import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Copy, Check, Download, FileJson } from 'lucide-react';

export default function JsonReportModal({ isOpen, onClose, report }) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const jsonString = report ? JSON.stringify(report, null, 2) : '{\n  "status": "NO_REPORT_AVAILABLE"\n}';

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `incident_${report?.incident_id || 'diagnostic'}_report.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="w-full max-w-4xl max-h-[85vh] bg-[#0c101c] border border-[#22314d] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f2c45] bg-[#0f1422]">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
                <FileJson className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Canonical JSON Diagnostic Report</h3>
                <p className="text-xs text-slate-400 font-mono">
                  Standardized Multi-Agent Protocol Artifact (Incident #{report?.incident_id || 'N/A'})
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#162136] hover:bg-[#202e4a] border border-[#223352] text-xs font-mono text-slate-200 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy JSON'}</span>
              </button>

              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#162136] hover:bg-[#202e4a] border border-[#223352] text-xs font-mono text-slate-200 transition-colors"
              >
                <Download className="w-3.5 h-3.5 text-cyan-400" />
                <span>Download</span>
              </button>

              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#1f2c45] transition-colors ml-2"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* JSON Body */}
          <div className="flex-1 overflow-auto p-4 bg-[#07090f]">
            <pre className="font-mono text-xs text-emerald-300 leading-relaxed">
              {jsonString}
            </pre>
          </div>

          {/* Footer */}
          <div className="px-5 py-3 border-t border-[#1f2c45] bg-[#0c101c] flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Status: <strong className="text-white">{report?.status || 'N/A'}</strong></span>
            <span>Confidence: <strong className="text-cyan-400">{Math.round((report?.confidence || 0) * 100)}%</strong></span>
            <span>Schema Version: <strong className="text-slate-300">1.0.0</strong></span>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
