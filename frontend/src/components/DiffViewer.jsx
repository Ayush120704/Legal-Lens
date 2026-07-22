import React, { useState } from 'react';

/**
 * DiffViewer - Side-by-side clause analysis with inline diff, quality scores,
 * pros/cons, suggestions, and compliance matches.
 */
export default function DiffViewer({ clauses }) {
  const [expandedIdx, setExpandedIdx] = useState(null);
  const [sortBy, setSortBy] = useState('risk');

  if (!clauses || clauses.length === 0) return null;

  // Sort clauses
  const sorted = [...clauses].sort((a, b) => {
    if (sortBy === 'risk') return (b.risk_score || 0) - (a.risk_score || 0);
    if (sortBy === 'category') return (a.category || '').localeCompare(b.category || '');
    return 0;
  });

  const toggleExpand = (idx) => {
    setExpandedIdx(expandedIdx === idx ? null : idx);
  };

  return (
    <div className="space-y-4">
      {/* Sort Controls */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-gray-500">Sort by:</span>
        <button
          onClick={() => setSortBy('risk')}
          className={`text-xs px-3 py-1 rounded-lg transition-all ${sortBy === 'risk' ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30' : 'text-gray-500 border border-gray-700/50 hover:border-gray-600'}`}
        >
          Risk Score
        </button>
        <button
          onClick={() => setSortBy('category')}
          className={`text-xs px-3 py-1 rounded-lg transition-all ${sortBy === 'category' ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/30' : 'text-gray-500 border border-gray-700/50 hover:border-gray-600'}`}
        >
          Category
        </button>
      </div>

      {/* Clause Cards */}
      {sorted.map((clause, idx) => {
        const isExpanded = expandedIdx === idx;
        const riskPercent = Math.round((clause.risk_score || 0) * 100);

        return (
          <div
            key={clause.id || idx}
            className={`glass-panel-sm overflow-hidden transition-all duration-300 ${
              clause.risk_level === 'high' ? 'border-accent-red/20' :
              clause.risk_level === 'medium' ? 'border-accent-amber/20' :
              'border-accent-green/20'
            }`}
          >
            {/* Clause Header */}
            <button
              onClick={() => toggleExpand(idx)}
              className="w-full text-left p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <span className={`risk-badge ${clause.risk_level}`}>
                  {clause.risk_level}
                </span>
                <span className="category-chip">{clause.category?.replace('_', ' ')}</span>
                <span className="text-xs text-gray-500 font-mono">{riskPercent}%</span>
              </div>
              <div className="flex items-center gap-2 ml-4">
                <span className="text-xs text-gray-500 hidden sm:inline">
                  {clause.flags?.length || 0} flags
                </span>
                <svg
                  className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>

            {/* Expanded Content */}
            {isExpanded && (
              <div className="px-4 pb-4 space-y-4 border-t border-white/5">
                {/* Side-by-Side Diff */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mt-4">
                  {/* Original */}
                  <div className="diff-removed rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-3.5 h-3.5 text-accent-red" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span className="text-xs font-semibold text-accent-red uppercase tracking-wider">Original</span>
                    </div>
                    <p className="text-sm text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">
                      {clause.original_text}
                    </p>
                  </div>

                  {/* Suggested */}
                  <div className="diff-added rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-3.5 h-3.5 text-accent-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-xs font-semibold text-accent-green uppercase tracking-wider">Suggested</span>
                    </div>
                    <p className="text-sm text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">
                      {clause.suggested_text}
                    </p>
                  </div>
                </div>

                {/* Quality Scores */}
                {clause.quality && (
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { label: 'Clarity', value: clause.quality.clarity_score, max: 2 },
                      { label: 'Balance', value: clause.quality.balance_score, max: 2 },
                      { label: 'Enforceability', value: clause.quality.enforceability_score, max: 1 },
                    ].map(({ label, value, max }) => {
                      const pct = max > 0 ? Math.max(0, ((value + max) / (max * 2)) * 100) : 50;
                      const color = value > 0 ? '#10b981' : value < 0 ? '#ef4444' : '#6b7280';
                      return (
                        <div key={label} className="bg-dark-900/60 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-gray-500">{label}</span>
                            <span className="text-xs font-mono" style={{ color }}>
                              {value > 0 ? '+' : ''}{value}
                            </span>
                          </div>
                          <div className="w-full bg-dark-600 rounded-full h-1.5">
                            <div
                              className="h-1.5 rounded-full transition-all duration-500"
                              style={{ width: `${pct}%`, backgroundColor: color }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Flags */}
                {clause.flags?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Risk Flags</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {clause.flags.map((flag, fi) => (
                        <span key={fi} className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-accent-red/10 text-accent-red text-xs border border-accent-red/20">
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
                          </svg>
                          {flag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Pros and Cons */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {clause.pros?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-accent-green uppercase tracking-wider mb-2">Strengths</h4>
                      <ul className="space-y-1">
                        {clause.pros.map((pro, pi) => (
                          <li key={pi} className="flex items-start gap-1.5 text-xs text-gray-400">
                            <svg className="w-3 h-3 mt-0.5 text-accent-green flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            {pro}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {clause.cons?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-accent-red uppercase tracking-wider mb-2">Weaknesses</h4>
                      <ul className="space-y-1">
                        {clause.cons.map((con, ci) => (
                          <li key={ci} className="flex items-start gap-1.5 text-xs text-gray-400">
                            <svg className="w-3 h-3 mt-0.5 text-accent-red flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            {con}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Suggestions */}
                {clause.suggestions?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-accent-blue uppercase tracking-wider mb-2">Suggestions</h4>
                    <ul className="space-y-1.5">
                      {clause.suggestions.map((sug, si) => (
                        <li key={si} className="flex items-start gap-2 text-xs text-gray-300 bg-dark-900/40 rounded-lg px-3 py-2">
                          <svg className="w-3.5 h-3.5 mt-0.5 text-accent-blue flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                          </svg>
                          {sug}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* LLM Analysis */}
                {clause.llm_analysis && (
                  <div>
                    <h4 className="text-xs font-semibold text-accent-purple uppercase tracking-wider mb-2">AI Legal Analysis</h4>
                    <div className="bg-dark-900/40 rounded-lg p-3 border border-accent-purple/10 space-y-2">
                      {clause.llm_analysis.legal_analysis && (
                        <p className="text-xs text-gray-300"><span className="text-accent-purple">Analysis:</span> {clause.llm_analysis.legal_analysis}</p>
                      )}
                      {clause.llm_analysis.legal_risk_details && (
                        <p className="text-xs text-accent-red"><span className="text-accent-red">Risks:</span> {clause.llm_analysis.legal_risk_details}</p>
                      )}
                      {clause.llm_analysis.negotiation_tips && Array.isArray(clause.llm_analysis.negotiation_tips) && (
                        <div>
                          <span className="text-xs text-accent-amber">Negotiation Tips:</span>
                          <ul className="mt-1 space-y-1">
                            {clause.llm_analysis.negotiation_tips.map((tip, ti) => (
                              <li key={ti} className="flex items-start gap-1.5 text-xs text-gray-400">
                                <svg className="w-3 h-3 mt-0.5 text-accent-amber flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                                {tip}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {clause.llm_analysis.jurisdiction_notes && (
                        <p className="text-xs text-gray-500"><span className="text-gray-400">Jurisdiction:</span> {clause.llm_analysis.jurisdiction_notes}</p>
                      )}
                    </div>
                  </div>
                )}

                {/* Compliance Matches */}
                {clause.compliance_matches?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-accent-purple uppercase tracking-wider mb-2">Compliance Matches</h4>
                    <div className="space-y-2">
                      {clause.compliance_matches.map((match, mi) => (
                        <div key={mi} className="bg-dark-900/40 rounded-lg p-3 border border-accent-purple/10">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-mono text-accent-purple">{match.id}</span>
                            {match.relevance_score != null && (
                              <span className="text-xs text-gray-500">relevance: {(match.relevance_score * 100).toFixed(1)}%</span>
                            )}
                          </div>
                          <p className="text-xs text-gray-400 leading-relaxed">{match.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
