const API_BASE = import.meta.env.VITE_API_URL || '/api';

export function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function register(email, password, displayName) {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Registration failed');
  }
  return response.json();
}

export async function login(email, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Login failed');
  }
  return response.json();
}

export async function getProfile() {
  const response = await fetch(`${API_BASE}/auth/me`, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Auth failed');
  return response.json();
}

export async function uploadDocument(text) {
  const response = await fetch(`${API_BASE}/session/upload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Upload failed with status ${response.status}`);
  }
  return response.json();
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE}/session/upload-file`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `File upload failed with status ${response.status}`);
  }
  return response.json();
}

export async function fetchJobStatus(jobId) {
  const response = await fetch(`${API_BASE}/session/status/${jobId}`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Status fetch failed with status ${response.status}`);
  }
  return response.json();
}

export async function listDocuments() {
  const response = await fetch(`${API_BASE}/documents`, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Failed to list documents');
  return response.json();
}

export async function getDocument(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}`, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Failed to get document');
  return response.json();
}

export async function deleteDocument(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}`, { method: 'DELETE', headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Failed to delete document');
  return response.json();
}

export async function chatWithDocument(documentId, question) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ question, document_id: documentId }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Chat failed');
  }
  return response.json();
}

export async function getChatHistory(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/chat/history`, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error('Failed to get chat history');
  return response.json();
}

export async function compareDocuments(docIdA, docIdB) {
  const response = await fetch(`${API_BASE}/documents/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ document_id_a: docIdA, document_id_b: docIdB }),
  });
  if (!response.ok) throw new Error('Comparison failed');
  return response.json();
}

export async function batchUpload(documents) {
  const response = await fetch(`${API_BASE}/session/batch-upload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ documents }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Batch upload failed');
  }
  return response.json();
}

export function connectWebSocket(jobId, { onMessage, onError }) {
  const wsBase = import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/^http/, 'ws')
    : null;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = wsBase
    ? `${wsBase}/ws/analysis/${jobId}`
    : `${protocol}//${window.location.host}/ws/analysis/${jobId}`;
  const ws = new WebSocket(wsUrl);

  let pingInterval = null;

  ws.onopen = () => {
    pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type !== 'pong') {
        onMessage(data);
      }
    } catch (e) {}
  };

  ws.onerror = (event) => {
    if (onError) onError(event);
  };

  ws.onclose = () => {
    if (pingInterval) clearInterval(pingInterval);
  };

  return {
    stop: () => {
      if (pingInterval) clearInterval(pingInterval);
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    },
  };
}

export function pollJobStatus(jobId, intervalMs, onProgress) {
  let intervalId = null;
  let stopped = false;

  const poll = async () => {
    if (stopped) return;
    try {
      const status = await fetchJobStatus(jobId);
      onProgress(status);
      if (status.status === 'completed' || status.status === 'error') {
        stop();
      }
    } catch (e) {}
  };

  intervalId = setInterval(poll, intervalMs);
  poll();

  const stop = () => {
    stopped = true;
    if (intervalId) clearInterval(intervalId);
  };

  return { stop };
}
