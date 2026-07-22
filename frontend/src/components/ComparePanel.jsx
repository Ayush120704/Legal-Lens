import React, { useState, useEffect } from 'react';
import { listDocuments, compareDocuments } from '../utils/api';

export default function ComparePanel() {
  const [docs, setDocs] = useState([]);
  const [docA, setDocA] = useState('');
  const [docB, setDocB] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    listDocuments().then(setDocs).catch(() => {});
  }, []);

  const handleCompare = async () => {
    if (!docA || !docB) return;
    setError('');
    setLoading(true);
    try {
      const res = await compareDocuments(parseInt(docA), parseInt(docB));
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel p-5">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Compare Documents</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Document A</label>
          <select
            value={docA}
            onChange={(e) => setDocA(e.target.value)}
            className="w-full bg-dark-900/60 border border-gray-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-accent-blue/40"
          >
            <option value="">Select document...</option>
            {docs.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Document B</label>
          <select
            value={docB}
            onChange={(e) => setDocB(e.target.value)}
            className="w-full bg-dark-900/60 border border-gray-700/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-accent-blue/40"
          >
            <option value="">Select document...</option>
            {docs.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}
          </select>
        </div>
      </div>

      <button
        onClick={handleCompare}
        disabled={!docA || !docB || loading || docA === docB}
        className="w-full py-2.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-accent-blue to-accent-purple text-white hover:shadow-lg transition-all disabled:opacity-40"
      >
        {loading ? 'Comparing...' : 'Compare Documents'}
      </button>

      {error && (
        <div className="mt-3 px-4 py-2 rounded-lg bg-accent-red/10 border border-accent-red/20 text-accent-red text-xs">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span>Doc A Health: <span className="text-white">{result.doc_a?.health_score ?? 'N/A'}</span></span>
            <span>Doc B Health: <span className="text-white">{result.doc_b?.health_score ?? 'N/A'}</span></span>
            {result.doc_a?.health_score != null && result.doc_b?.health_score != null && (
              <span className={result.doc_b.health_score > result.doc_a.health_score ? 'text-accent-green' : 'text-accent-red'}>
                Delta: {(result.doc_b.health_score - result.doc_a.health_score).toFixed(1)}
              </span>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto space-y-2">
            {result.comparison.map((item, i) => (
              <div key={i} className="bg-dark-900/40 rounded-lg p-3 border border-gray-700/30">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold text-gray-500">#{item.index}</span>
                  {item.risk_delta != null && (
                    <span className={`text-xs ${item.risk_delta > 0 ? 'text-accent-red' : item.risk_delta < 0 ? 'text-accent-green' : 'text-gray-500'}`}>
                      Risk Δ: {item.risk_delta > 0 ? '+' : ''}{item.risk_delta.toFixed(2)}
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500">A: </span>
                    <span className={`${item.doc_a?.risk_level === 'high' ? 'text-accent-red' : item.doc_a?.risk_level === 'medium' ? 'text-accent-amber' : 'text-accent-green'}`}>
                      {item.doc_a?.risk_level || '-'} ({item.doc_a?.risk_score != null ? (item.doc_a.risk_score * 100).toFixed(0) + '%' : '-'})
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">B: </span>
                    <span className={`${item.doc_b?.risk_level === 'high' ? 'text-accent-red' : item.doc_b?.risk_level === 'medium' ? 'text-accent-amber' : 'text-accent-green'}`}>
                      {item.doc_b?.risk_level || '-'} ({item.doc_b?.risk_score != null ? (item.doc_b.risk_score * 100).toFixed(0) + '%' : '-'})
                    </span>
                  </div>
                </div>
                {item.llm_comparison && (
                  <p className="text-xs text-gray-500 mt-2 italic">{item.llm_comparison.slice(0, 200)}...</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
