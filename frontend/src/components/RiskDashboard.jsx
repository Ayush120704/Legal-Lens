import React from 'react';
import { getAuthHeaders } from '../utils/api';

function downloadExport(documentId, format) {
  const API_BASE = import.meta.env.VITE_API_URL || '/api';
  fetch(`${API_BASE}/documents/${documentId}/export/${format}`, { headers: getAuthHeaders() })
    .then(r => r.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `legallens_report_${documentId}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    })
    .catch(() => {});
}

export default function RiskDashboard({ jobStatus, documentId }) {
  if (!jobStatus) return null;

  const { progress, status, risk_summary, document_summary, total_clauses, processed_clauses } = jobStatus;

  const healthScore = document_summary?.health_score ?? 0;
  const overallHealth = document_summary?.overall_health ?? 'unknown';
  const circumference = 2 * Math.PI * 42;
  const dashOffset = circumference - (healthScore / 100) * circumference;

  const healthColor = { good: '#10b981', moderate: '#f59e0b', concerning: '#f97316', critical: '#ef4444' }[overallHealth] || '#6b7280';
  const isProcessing = status === 'processing';

  return (
    <div className="space-y-5">
      {isProcessing && (
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></div>
              <span className="text-sm font-medium text-accent-blue">Analyzing Document...</span>
            </div>
            <span className="text-xs text-gray-400">{processed_clauses}/{total_clauses} clauses</span>
          </div>
          <div className="w-full bg-dark-900/60 rounded-full h-2">
            <div className="progress-bar h-2 rounded-full bg-gradient-to-r from-accent-blue to-accent-purple" style={{ width: `${progress}%` }} />
          </div>
          <p className="text-xs text-gray-500 mt-2">{progress}% complete</p>
        </div>
      )}

      {document_summary && (
        <>
          <div className="glass-panel p-6">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-5">Document Health</h3>
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <div className="health-ring flex-shrink-0">
                <svg width="100" height="100">
                  <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
                  <circle cx="50" cy="50" r="42" fill="none" stroke={healthColor} strokeWidth="6" strokeLinecap="round"
                    strokeDasharray={circumference} strokeDashoffset={dashOffset}
                    style={{ transition: 'stroke-dashoffset 1s ease-out, stroke 0.5s ease' }} />
                </svg>
                <div className="value" style={{ color: healthColor }}>{healthScore}</div>
              </div>
              <div className="flex-1 text-center sm:text-left">
                <p className="text-lg font-semibold text-white mb-1">{document_summary.verdict}</p>
                <div className="flex flex-wrap justify-center sm:justify-start gap-3 mt-3">
                  <span className="risk-badge high"><span className="w-1.5 h-1.5 rounded-full bg-accent-red"></span>{risk_summary?.high_risk_count ?? 0} High</span>
                  <span className="risk-badge medium"><span className="w-1.5 h-1.5 rounded-full bg-accent-amber"></span>{risk_summary?.medium_risk_count ?? 0} Medium</span>
                  <span className="risk-badge low"><span className="w-1.5 h-1.5 rounded-full bg-accent-green"></span>{risk_summary?.low_risk_count ?? 0} Low</span>
                </div>
              </div>
            </div>
          </div>

          {/* LLM Executive Summary */}
          {document_summary.llm_executive_summary && (
            <div className="glass-panel p-5 border border-accent-purple/20">
              <h3 className="text-sm font-semibold text-accent-purple uppercase tracking-wider mb-3">AI Executive Summary</h3>
              <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{document_summary.llm_executive_summary}</p>
            </div>
          )}

          {/* Export Buttons */}
          {documentId && status === 'completed' && (
            <div className="glass-panel p-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Export Report</h3>
              <div className="flex gap-2">
                <button onClick={() => downloadExport(documentId, 'csv')}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent-blue/10 text-accent-blue border border-accent-blue/30 text-xs font-medium hover:bg-accent-blue/20 transition-all">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  CSV
                </button>
                <button onClick={() => downloadExport(documentId, 'txt')}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent-green/10 text-accent-green border border-accent-green/30 text-xs font-medium hover:bg-accent-green/20 transition-all">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  TXT Report
                </button>
              </div>
            </div>
          )}

          {/* Key Findings */}
          {document_summary?.key_findings?.length > 0 && (
            <div className="glass-panel p-5">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Key Findings</h3>
              <ul className="space-y-2">
                {document_summary.key_findings.map((finding, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                    <svg className="w-4 h-4 mt-0.5 text-accent-amber flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.27 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    {finding}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Missing Protections */}
          {document_summary?.missing_protections?.length > 0 && (
            <div className="glass-panel p-5">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Missing Protections</h3>
              <div className="flex flex-wrap gap-2">
                {document_summary.missing_protections.map((mp, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-dark-900/60 border border-gray-700/40 text-xs text-gray-400">
                    <svg className="w-3 h-3 text-accent-red" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    {mp.description}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Critical Issues */}
          {document_summary?.critical_issues?.length > 0 && (
            <div className="glass-panel p-5 border border-accent-red/20">
              <h3 className="text-sm font-semibold text-accent-red uppercase tracking-wider mb-3">Critical Issues</h3>
              <div className="space-y-3">
                {document_summary.critical_issues.map((issue, i) => (
                  <div key={i} className="bg-dark-900/60 rounded-lg p-3 border border-accent-red/10">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="risk-badge high" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
                        Score: {(issue.risk_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 font-mono mt-1">{issue.clause_preview}</p>
                    <p className="text-xs text-accent-amber mt-1">{issue.primary_issue}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Risk Patterns */}
          {document_summary?.top_risk_patterns?.length > 0 && (
            <div className="glass-panel p-5">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Top Risk Patterns</h3>
              <div className="space-y-2">
                {document_summary.top_risk_patterns.map((pattern, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-300">{pattern.pattern}</span>
                    <span className="text-xs text-gray-500 font-mono">x{pattern.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
