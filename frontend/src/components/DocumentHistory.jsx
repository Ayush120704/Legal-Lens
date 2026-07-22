import React, { useState, useEffect } from 'react';
import { listDocuments, deleteDocument } from '../utils/api';

export default function DocumentHistory({ onSelectDocument }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadDocs = async () => {
    try {
      const result = await listDocuments();
      setDocs(result);
    } catch (e) {
      console.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadDocs(); }, []);

  const handleDelete = async (id) => {
    try {
      await deleteDocument(id);
      setDocs(docs.filter(d => d.id !== id));
    } catch (e) {
      console.error('Delete failed');
    }
  };

  if (loading) {
    return (
      <div className="glass-panel p-5">
        <p className="text-sm text-gray-500">Loading documents...</p>
      </div>
    );
  }

  if (docs.length === 0) {
    return (
      <div className="glass-panel p-5">
        <p className="text-sm text-gray-500">No documents analyzed yet. Upload a contract to get started.</p>
      </div>
    );
  }

  const healthColor = { good: 'text-accent-green', moderate: 'text-accent-amber', concerning: 'text-orange-400', critical: 'text-accent-red' };

  return (
    <div className="glass-panel p-5">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Document History</h3>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {docs.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center justify-between p-3 rounded-lg bg-dark-900/40 border border-gray-700/30 hover:border-accent-blue/30 cursor-pointer transition-all group"
            onClick={() => onSelectDocument(doc.id)}
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate">{doc.title}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-xs font-mono ${healthColor[doc.overall_health] || 'text-gray-500'}`}>
                  {doc.overall_health ? `${doc.health_score || 'N/A'} - ${doc.overall_health}` : 'Processing...'}
                </span>
                <span className="text-xs text-gray-600">{new Date(doc.created_at).toLocaleDateString()}</span>
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
              className="ml-2 p-1.5 rounded-lg text-gray-600 hover:text-accent-red hover:bg-accent-red/10 opacity-0 group-hover:opacity-100 transition-all"
              title="Delete"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
