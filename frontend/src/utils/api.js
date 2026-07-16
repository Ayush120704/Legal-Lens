const API_BASE = '/api';

/**
 * Upload a document for analysis.
 * @param {string} text - The document text to analyze.
 * @returns {Promise<{job_id: string, message: string}>}
 */
export async function uploadDocument(text) {
  const response = await fetch(`${API_BASE}/session/upload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Upload failed with status ${response.status}`);
  }
  return response.json();
}

/**
 * Upload a file (PDF or TXT) for server-side text extraction and analysis.
 * @param {File} file - The File object to upload.
 * @returns {Promise<{job_id: string, message: string}>}
 */
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE}/session/upload-file`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `File upload failed with status ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch the current status of an analysis job.
 * @param {string} jobId
 * @returns {Promise<Object>} Job status object with clauses, progress, etc.
 */
export async function fetchJobStatus(jobId) {
  const response = await fetch(`${API_BASE}/session/status/${jobId}`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Status fetch failed with status ${response.status}`);
  }
  return response.json();
}

/**
 * Connect to the WebSocket for real-time analysis progress.
 * @param {string} jobId
 * @param {Object} callbacks - { onMessage: fn, onError: fn }
 * @returns {{ stop: () => void }} Call stop() to disconnect.
 */
export function connectWebSocket(jobId, { onMessage, onError }) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/analysis/${jobId}`;
  const ws = new WebSocket(wsUrl);

  // Keepalive ping every 30 seconds
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
    } catch (e) {
      // Ignore non-JSON messages
    }
  };

  ws.onerror = (event) => {
    if (onError) {
      onError(event);
    }
  };

  ws.onclose = () => {
    if (pingInterval) {
      clearInterval(pingInterval);
    }
  };

  return {
    stop: () => {
      if (pingInterval) {
        clearInterval(pingInterval);
      }
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    },
  };
}

/**
 * Poll the job status at regular intervals until completion.
 * @param {string} jobId
 * @param {number} intervalMs - Polling interval in milliseconds.
 * @param {function} onProgress - Callback invoked with each status update.
 * @returns {{ stop: () => void }} Call stop() to stop polling.
 */
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
    } catch (e) {
      // Continue polling even on error
    }
  };

  intervalId = setInterval(poll, intervalMs);
  // Immediate first poll
  poll();

  const stop = () => {
    stopped = true;
    if (intervalId) {
      clearInterval(intervalId);
    }
  };

  return { stop };
}
