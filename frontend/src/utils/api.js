// VITE_API_URL must be set at build time (Vite inlines it).
// Without it, relative /api/* calls go to the same host with no proxy.
const _apiUrl = import.meta.env.VITE_API_URL;
const API_BASE = _apiUrl ? `${_apiUrl}/api` : '/api';
export const BASE_URL = _apiUrl || '/api';

export function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function api(path, options = {}) {
  const { method = 'GET', body, headers = {}, formData } = options;
  const isFormData = formData instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: isFormData ? { ...getAuthHeaders(), ...headers } : { 'Content-Type': 'application/json', ...getAuthHeaders(), ...headers },
    body: formData || (body ? JSON.stringify(body) : undefined),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed with status ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

// Auth
export const register = (email, password, displayName) =>
  api('/auth/register', { method: 'POST', body: { email, password, display_name: displayName } });

export const login = (email, password) =>
  api('/auth/login', { method: 'POST', body: { email, password } });

export const getProfile = () => api('/auth/me', { headers: getAuthHeaders() });

export const updateProfile = (data) =>
  api('/auth/me', { method: 'PUT', body: data, headers: getAuthHeaders() });

// Session / Upload
export const uploadDocument = (text) =>
  api('/session/upload', { method: 'POST', body: { text }, headers: getAuthHeaders() });

export const uploadFile = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api('/session/upload-file', { method: 'POST', formData, headers: getAuthHeaders() });
};

export const batchUpload = (documents) =>
  api('/session/batch-upload', { method: 'POST', body: { documents }, headers: getAuthHeaders() });

// Documents CRUD
export const listDocuments = () => api('/documents', { headers: getAuthHeaders() });

export const getDocument = (documentId) => api(`/documents/${documentId}`, { headers: getAuthHeaders() });

export const deleteDocument = (documentId) =>
  api(`/documents/${documentId}`, { method: 'DELETE', headers: getAuthHeaders() });

// Export
export async function exportDocument(documentId, format) {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE}/documents/${documentId}/export/${format}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Export failed with status ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `legallens_report_${documentId}.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

// Chat
export const chatWithDocument = (documentId, question) =>
  api(`/documents/${documentId}/chat`, { method: 'POST', body: { question, document_id: documentId }, headers: getAuthHeaders() });

export const getChatHistory = (documentId) =>
  api(`/documents/${documentId}/chat/history`, { headers: getAuthHeaders() });

// Compare
export const compareDocuments = (docIdA, docIdB) =>
  api('/documents/compare', { method: 'POST', body: { document_id_a: docIdA, document_id_b: docIdB }, headers: getAuthHeaders() });

// Polling — polls the Document endpoint for progress
export function pollDocumentStatus(documentId, intervalMs, onProgress) {
  let intervalId = null;
  let stopped = false;

  const poll = async () => {
    if (stopped) return;
    try {
      const doc = await getDocument(documentId);
      onProgress(doc);
      if (doc.status === 'completed' || doc.status === 'error') stop();
    } catch (e) { /* ignore */ }
  };

  intervalId = setInterval(poll, intervalMs);
  poll();

  const stop = () => {
    stopped = true;
    if (intervalId) clearInterval(intervalId);
  };

  return { stop };
}
