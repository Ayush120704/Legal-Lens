import React, { useState, useRef, useEffect, useCallback } from 'react';
import VectorBackground3D from './components/VectorBackground3D';
import DocumentUpload from './components/DocumentUpload';
import RiskDashboard from './components/RiskDashboard';
import DiffViewer from './components/DiffViewer';
import { uploadDocument, uploadFile, connectWebSocket, pollJobStatus } from './utils/api';

export default function App() {
  const [jobStatus, setJobStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState('dashboard');

  const wsRef = useRef(null);
  const pollRef = useRef(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.stop();
      if (pollRef.current) pollRef.current.stop();
    };
  }, []);

  const handleAnalyze = useCallback(async (text, file) => {
    setIsLoading(true);
    setError(null);
    setJobStatus(null);

    try {
      let result;
      if (file) {
        result = await uploadFile(file);
      } else {
        result = await uploadDocument(text);
      }
      const { job_id } = result;

      // Try WebSocket first
      let wsConnected = false;
      try {
        wsRef.current = connectWebSocket(job_id, {
          onMessage: (data) => {
            if (data.type === 'progress') {
              setJobStatus((prev) => ({
                ...prev,
                job_id,
                status: data.status,
                progress: data.progress,
                processed_clauses: data.processed_clauses,
                total_clauses: data.total_clauses,
              }));
            } else if (data.type === 'complete') {
              setJobStatus(data.data);
              setIsLoading(false);
            } else if (data.type === 'error') {
              setError(data.message || 'Analysis failed');
              setIsLoading(false);
            }
          },
          onError: () => {
            wsConnected = false;
          },
        });
        wsConnected = true;
      } catch (e) {
        wsConnected = false;
      }

      // Fall back to polling if WebSocket fails
      if (!wsConnected) {
        pollRef.current = pollJobStatus(job_id, 1000, (status) => {
          setJobStatus(status);
          if (status.status === 'completed' || status.status === 'error') {
            setIsLoading(false);
          }
        });
      }

      // Initial status fetch
      const initialStatus = await import('./utils/api').then((m) =>
        m.fetchJobStatus(job_id)
      );
      setJobStatus(initialStatus);
      if (initialStatus.status === 'completed' || initialStatus.status === 'error') {
        setIsLoading(false);
      }
    } catch (e) {
      setError(e.message || 'Failed to start analysis');
      setIsLoading(false);
    }
  }, []);

  const clauses = jobStatus?.clauses || [];
  const isComplete = jobStatus?.status === 'completed';

  return (
    <div className="min-h-screen relative">
      {/* 3D Background */}
      <VectorBackground3D />

      {/* Main Content */}
      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-white/5 backdrop-blur-md bg-dark-900/60">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
                </svg>
              </div>
              <div>
                <h1 className="text-base font-bold text-white tracking-tight">LegalLens</h1>
                <p className="text-[10px] text-gray-500 uppercase tracking-widest">AI Document Analyzer</p>
              </div>
            </div>

            {/* View Toggle (shown when results exist) */}
            {isComplete && clauses.length > 0 && (
              <div className="flex items-center gap-1 bg-dark-800/80 rounded-lg p-1">
                <button
                  onClick={() => setActiveView('dashboard')}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    activeView === 'dashboard'
                      ? 'bg-accent-blue/20 text-accent-blue'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setActiveView('clauses')}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    activeView === 'clauses'
                      ? 'bg-accent-blue/20 text-accent-blue'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  Clause Analysis
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Body */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Hero (shown when no results) */}
          {!jobStatus && !isLoading && (
            <div className="text-center mb-10">
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-3">
                AI-Powered Legal Risk{' '}
                <span className="bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent">
                  Intelligence
                </span>
              </h2>
              <p className="text-gray-400 max-w-2xl mx-auto text-sm sm:text-base">
                Upload any contract or legal document. Our AI agent architecture scores risk using
                a custom 60/40 weighted formula, matches compliance guidelines via vector search,
                and delivers an interactive clause-by-clause breakdown.
              </p>
            </div>
          )}

          {/* Upload Section */}
          <div className={`mx-auto mb-8 ${jobStatus ? 'max-w-3xl' : 'max-w-3xl'}`}>
            <DocumentUpload onAnalyze={handleAnalyze} isLoading={isLoading} />
          </div>

          {/* Error */}
          {error && (
            <div className="max-w-3xl mx-auto mb-6 glass-panel p-4 border border-accent-red/30">
              <div className="flex items-center gap-2 text-accent-red text-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {error}
              </div>
            </div>
          )}

          {/* Results */}
          {jobStatus && (
            <div className="mt-2">
              {activeView === 'dashboard' ? (
                <div className="max-w-3xl mx-auto">
                  <RiskDashboard jobStatus={jobStatus} />
                </div>
              ) : (
                <DiffViewer clauses={clauses} />
              )}
            </div>
          )}
        </main>

        {/* Footer */}
        <footer className="border-t border-white/5 py-6 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p className="text-xs text-gray-600">
              Built with FastAPI, React, Three.js, sentence-transformers, and ChromaDB
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}
