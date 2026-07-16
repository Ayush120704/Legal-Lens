import React, { useState, useRef } from 'react';
import { uploadFile } from '../utils/api';

const SAMPLE_CONTRACT = `Section 1. Automatic Renewal. This Agreement shall automatically renew for successive twelve-month periods unless either party provides written notice of non-renewal at least sixty (60) days prior to the end of the current term. No opt-out mechanism is provided.

Section 2. Unlimited Liability. The Client bears unlimited liability for all direct, indirect, consequential, incidental, and punitive damages arising out of or related to this Agreement, regardless of the form of action or theory of liability.

Section 3. Termination. Either party may terminate this Agreement at any time, for any reason or no reason, without prior written notice. Upon termination, no refunds shall be issued for any fees previously paid, and all outstanding obligations immediately become due.

Section 4. Indemnification. The Client shall indemnify, defend, and hold harmless the Provider, its officers, directors, employees, agents, and affiliates from and against any and all claims, damages, losses, costs, and expenses (including reasonable attorneys' fees) arising from the Client's use of the services or breach of this Agreement.

Section 5. Data Privacy and GDPR Compliance. Provider shall comply with GDPR Article 33 regarding breach notification within 72 hours and GDPR Article 7 regarding consent requirements. Provider shall implement appropriate technical and organizational measures to ensure data protection.

Section 6. Binding Arbitration. Any dispute, controversy, or claim arising out of or relating to this Agreement shall be resolved exclusively through binding arbitration administered by the American Arbitration Association. Both parties waive their right to jury trial and class action participation.

Section 7. Confidentiality. The Client shall maintain strict confidentiality of all proprietary information received during the term of this Agreement. This obligation shall survive termination indefinitely without time limitation.

Section 8. Intellectual Property. All work product, inventions, and materials created under this Agreement shall be the sole and exclusive property of the Provider. The Client assigns all rights, title, and interest in such work product to the Provider without compensation.`;

export default function DocumentUpload({ onAnalyze, isLoading }) {
  const [text, setText] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState('');
  const [isPdfMode, setIsPdfMode] = useState(false);
  const [pdfFile, setPdfFile] = useState(null);
  const [pdfError, setPdfError] = useState('');
  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isLoading) return;

    if (isPdfMode && pdfFile) {
      onAnalyze(null, pdfFile);
    } else if (text.trim()) {
      onAnalyze(text.trim(), null);
    }
  };

  const handleLoadSample = () => {
    setText(SAMPLE_CONTRACT);
    setFileName('sample-contract.txt');
    setIsPdfMode(false);
    setPdfFile(null);
    setPdfError('');
  };

  const handleClear = () => {
    setText('');
    setFileName('');
    setIsPdfMode(false);
    setPdfFile(null);
    setPdfError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) processFile(file);
  };

  const processFile = (file) => {
    setPdfError('');
    const nameLower = file.name.toLowerCase();
    const isPdf = nameLower.endsWith('.pdf');
    const isTxt = nameLower.endsWith('.txt') || nameLower.endsWith('.md');

    if (isPdf) {
      setFileName(file.name);
      setIsPdfMode(true);
      setPdfFile(file);
      setText('');
    } else if (isTxt) {
      setFileName(file.name);
      setIsPdfMode(false);
      setPdfFile(null);
      const reader = new FileReader();
      reader.onload = (e) => {
        setText(e.target.result);
      };
      reader.readAsText(file);
    } else {
      setPdfError('Unsupported file type. Please upload a .pdf, .txt, or .md file.');
    }
  };

  const hasContent = isPdfMode ? !!pdfFile : !!text.trim();
  const canSubmit = hasContent && !isLoading;

  return (
    <div className="glass-panel p-6 md:p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-accent-blue/20 flex items-center justify-center">
          <svg className="w-5 h-5 text-accent-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">Upload Document</h2>
          <p className="text-sm text-gray-400">Paste text or upload a PDF / TXT file for AI analysis</p>
        </div>
      </div>

      {/* Drag and Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-300 mb-4
          ${isDragging
            ? 'border-accent-blue bg-accent-blue/5 scale-[1.01]'
            : 'border-gray-700/50 hover:border-gray-600 hover:bg-white/[0.02]'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.pdf"
          onChange={handleFileSelect}
          className="hidden"
        />
        <svg className="w-8 h-8 mx-auto mb-2 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-sm text-gray-400">
          {fileName ? (
            <span className="text-accent-green">{fileName}</span>
          ) : (
            <>Drag & drop a <span className="text-white font-medium">.pdf</span> or <span className="text-white font-medium">.txt</span> file here, or <span className="text-accent-blue font-medium">browse</span></>
          )}
        </p>
        {isPdfMode && pdfFile && (
          <p className="text-xs text-accent-purple mt-2">
            PDF will be parsed server-side for text extraction
          </p>
        )}
      </div>

      {/* PDF Error */}
      {pdfError && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-accent-red/10 border border-accent-red/20 text-accent-red text-xs">
          {pdfError}
        </div>
      )}

      {/* Text Area (hidden in PDF mode) */}
      {!isPdfMode && (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Or paste your legal document text here..."
          rows={10}
          className="
            w-full bg-dark-900/60 border border-gray-700/50 rounded-xl px-4 py-3
            text-sm text-gray-200 placeholder-gray-600 resize-none
            focus:outline-none focus:ring-2 focus:ring-accent-blue/40 focus:border-accent-blue/40
            transition-all duration-200 mb-4 font-mono leading-relaxed
          "
        />
      )}

      {/* PDF Preview */}
      {isPdfMode && pdfFile && (
        <div className="mb-4 p-4 rounded-xl bg-dark-900/60 border border-accent-purple/20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-purple/20 flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-accent-purple" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{pdfFile.name}</p>
              <p className="text-xs text-gray-500">{(pdfFile.size / 1024).toFixed(1)} KB</p>
            </div>
            <span className="px-2 py-1 rounded-md bg-accent-purple/15 text-accent-purple text-xs font-semibold">PDF</span>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className={`
            flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm transition-all duration-300
            ${canSubmit
              ? 'bg-gradient-to-r from-accent-blue to-accent-purple text-white hover:shadow-lg hover:shadow-accent-blue/25 hover:scale-[1.02] active:scale-[0.98]'
              : 'bg-dark-600 text-gray-500 cursor-not-allowed'
            }
          `}
        >
          {isLoading ? (
            <>
              <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }}></div>
              Analyzing...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              {isPdfMode ? 'Analyze PDF' : 'Analyze Document'}
            </>
          )}
        </button>

        <button
          onClick={handleLoadSample}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-gray-400 border border-gray-700/50 hover:border-gray-600 hover:text-white transition-all duration-200 disabled:opacity-40"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          Load Sample Contract
        </button>

        {hasContent && (
          <button
            onClick={handleClear}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-gray-500 hover:text-accent-red transition-all duration-200 disabled:opacity-40"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear
          </button>
        )}
      </div>

      {text && !isPdfMode && (
        <p className="text-xs text-gray-600 mt-3">
          {text.split(/\s+/).filter(Boolean).length} words · {text.length} characters
        </p>
      )}
    </div>
  );
}
