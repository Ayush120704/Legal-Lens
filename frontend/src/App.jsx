import React, { useState, useRef, useEffect, useCallback } from 'react';
import VectorBackground3D from './components/VectorBackground3D';
import DocumentUpload from './components/DocumentUpload';
import RiskDashboard from './components/RiskDashboard';
import DiffViewer from './components/DiffViewer';
import AuthModal from './components/AuthModal';
import DocumentHistory from './components/DocumentHistory';
import ChatPanel from './components/ChatPanel';
import ComparePanel from './components/ComparePanel';
import { uploadDocument, uploadFile, connectWebSocket, pollJobStatus, getDocument, getProfile } from './utils/api';

export default function App() {
  const [jobStatus, setJobStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState('dashboard');
  const [showAuth, setShowAuth] = useState(false);
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('analyze');
  const [documentId, setDocumentId] = useState(null);
  const [savedDocId, setSavedDocId] = useState(null);

  const wsRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      getProfile().then(setUser).catch(() => localStorage.removeItem('token'));
    }
  }, []);

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
    setDocumentId(null);
    setSavedDocId(null);

    try {
      let result;
      if (file) {
        result = await uploadFile(file);
      } else {
        result = await uploadDocument(text);
      }
      const { job_id, document_id } = result;
      setDocumentId(document_id);

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
              if (document_id) {
                getDocument(document_id).then(d => setSavedDocId(d.id)).catch(() => {});
              }
            } else if (data.type === 'error') {
              setError(data.message || 'Analysis failed');
              setIsLoading(false);
            }
          },
          onError: () => { wsConnected = false; },
        });
        wsConnected = true;
      } catch (e) {
        wsConnected = false;
      }

      if (!wsConnected) {
        pollRef.current = pollJobStatus(job_id, 1000, (status) => {
          setJobStatus(status);
          if (status.status === 'completed' || status.status === 'error') {
            setIsLoading(false);
          }
        });
      }

      const initialStatus = await import('./utils/api').then((m) => m.fetchJobStatus(job_id));
      setJobStatus(initialStatus);
      if (initialStatus.status === 'completed' || initialStatus.status === 'error') {
        setIsLoading(false);
      }
    } catch (e) {
      setError(e.message || 'Failed to start analysis');
      setIsLoading(false);
    }
  }, []);

  const handleSelectDocument = async (id) => {
    try {
      const doc = await getDocument(id);
      setJobStatus({
        job_id: doc.job_id,
        status: doc.status,
        progress: doc.progress,
        total_clauses: doc.total_clauses,
        processed_clauses: doc.processed_clauses,
        clauses: doc.clauses,
        risk_summary: doc.risk_summary,
        document_summary: doc.document_summary,
      });
      setSavedDocId(doc.id);
      setActiveView('dashboard');
      setActiveTab('analyze');
    } catch (e) {
      setError('Failed to load document');
    }
  };

  const clauses = jobStatus?.clauses || [];
  const isComplete = jobStatus?.status === 'completed';

  return (
    <div className="min-h-screen relative">
      <VectorBackground3D />

      <div className="relative z-10">
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

            <div className="flex items-center gap-3">
              {/* View Toggle */}
              {isComplete && clauses.length > 0 && activeTab === 'analyze' && (
                <div className="flex items-center gap-1 bg-dark-800/80 rounded-lg p-1">
                  <button onClick={() => setActiveView('dashboard')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${activeView === 'dashboard' ? 'bg-accent-blue/20 text-accent-blue' : 'text-gray-500 hover:text-gray-300'}`}>
                    Dashboard
                  </button>
                  <button onClick={() => setActiveView('clauses')}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${activeView === 'clauses' ? 'bg-accent-blue/20 text-accent-blue' : 'text-gray-500 hover:text-gray-300'}`}>
                    Clause Analysis
                  </button>
                </div>
              )}

              {/* Auth */}
              {user ? (
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 hidden sm:inline">{user.display_name}</span>
                  <button onClick={() => { setUser(null); localStorage.removeItem('token'); }}
                    className="text-xs text-gray-500 hover:text-accent-red transition-colors">
                    Sign Out
                  </button>
                </div>
              ) : (
                <button onClick={() => setShowAuth(true)}
                  className="text-xs px-4 py-2 rounded-lg bg-accent-blue/10 text-accent-blue border border-accent-blue/30 hover:bg-accent-blue/20 transition-all">
                  Sign In
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
          <div className="flex gap-1 bg-dark-800/60 rounded-lg p-1 w-fit">
            {[
              { key: 'analyze', label: 'Analyze', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
              { key: 'history', label: 'History', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
              { key: 'compare', label: 'Compare', icon: 'M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z' },
            ].map(tab => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-medium transition-all ${activeTab === tab.key ? 'bg-accent-blue/20 text-accent-blue' : 'text-gray-500 hover:text-gray-300'}`}>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
                </svg>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {activeTab === 'analyze' && (
            <>
              {!jobStatus && !isLoading && (
                <div className="text-center mb-10">
                  <h2 className="text-3xl sm:text-4xl font-bold text-white mb-3">
                    AI-Powered Legal Risk{' '}
                    <span className="bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent">Intelligence</span>
                  </h2>
                  <p className="text-gray-400 max-w-2xl mx-auto text-sm sm:text-base">
                    Upload any contract or legal document. Our AI analyzes risk using semantic embeddings + keyword scoring,
                    matches compliance guidelines via vector search, and delivers an interactive clause-by-clause breakdown.
                  </p>
                </div>
              )}

              <div className={`mx-auto mb-8 ${jobStatus ? 'max-w-3xl' : 'max-w-3xl'}`}>
                <DocumentUpload onAnalyze={handleAnalyze} isLoading={isLoading} />
              </div>

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

              {jobStatus && (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mt-2">
                  {/* Left spacer to center the analysis panel */}
                  <div className="hidden lg:block"></div>

                  <div className={`${activeView === 'dashboard' ? 'lg:col-span-2' : 'lg:col-span-3'}`}>
                    {activeView === 'dashboard' ? (
                      <div className="max-w-3xl">
                        <RiskDashboard jobStatus={jobStatus} documentId={savedDocId} />
                      </div>
                    ) : (
                      <DiffViewer clauses={clauses} />
                    )}
                  </div>

                  {/* Chat Panel Sidebar */}
                  {isComplete && savedDocId && (
                    <div className="lg:col-span-1">
                      <ChatPanel documentId={savedDocId} />
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {activeTab === 'history' && (
            <div className="max-w-2xl mx-auto">
              <DocumentHistory onSelectDocument={handleSelectDocument} />
            </div>
          )}

          {activeTab === 'compare' && (
            <div className="max-w-3xl mx-auto">
              <ComparePanel />
            </div>
          )}
        </main>

        <footer className="border-t border-white/5 py-6 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p className="text-xs text-gray-600">
              LegalLens v2.0 — Built with FastAPI, React, Three.js, sentence-transformers, ChromaDB, and OpenAI
            </p>
          </div>
        </footer>
      </div>

      <AuthModal
        isOpen={showAuth}
        onClose={() => setShowAuth(false)}
        onAuthSuccess={(userData) => setUser(userData)}
      />
    </div>
  );
}
