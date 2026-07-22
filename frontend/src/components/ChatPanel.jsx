import React, { useState, useEffect, useRef } from 'react';
import { chatWithDocument, getChatHistory } from '../utils/api';

export default function ChatPanel({ documentId }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (!documentId) return;
    setInitialLoading(true);
    getChatHistory(documentId)
      .then(setMessages)
      .catch(() => {})
      .finally(() => setInitialLoading(false));
  }, [documentId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;
    const q = question.trim();
    setQuestion('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setLoading(true);
    try {
      const result = await chatWithDocument(documentId, q);
      setMessages(prev => [...prev, { role: 'assistant', content: result.answer }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel flex flex-col" style={{ height: '400px' }}>
      <div className="px-5 py-4 border-b border-white/5">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Ask About This Document</h3>
        <p className="text-xs text-gray-600 mt-1">Ask questions about clauses, risks, or terms</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {initialLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }}></div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-xs text-gray-600 text-center">
              Try asking:<br />
              "What are the high-risk clauses?"<br />
              "Summarize the liability section"<br />
              "What should I negotiate?"
            </p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
                msg.role === 'user'
                  ? 'bg-accent-blue/20 text-accent-blue border border-accent-blue/20'
                  : 'bg-dark-900/60 text-gray-300 border border-gray-700/30'
              }`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-dark-900/60 rounded-xl px-4 py-2.5 border border-gray-700/30">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <form onSubmit={handleSend} className="p-4 border-t border-white/5 flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about this document..."
          className="flex-1 bg-dark-900/60 border border-gray-700/50 rounded-lg px-4 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-accent-blue/40"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!question.trim() || loading}
          className="px-4 py-2 rounded-lg bg-accent-blue/20 text-accent-blue border border-accent-blue/30 hover:bg-accent-blue/30 transition-all disabled:opacity-40"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </form>
    </div>
  );
}
