import axios from 'axios';

const configuredApiUrl = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/+$/, '');
const apiBaseUrl = configuredApiUrl
  ? configuredApiUrl.endsWith('/api')
    ? configuredApiUrl
    : `${configuredApiUrl}/api`
  : '/api';

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

const recentErrorLogs = new Map();

api.interceptors.response.use(undefined, (error) => {
  if (error.code !== 'ERR_CANCELED') {
    const request = error.config || {};
    const method = (request.method || 'GET').toUpperCase();
    const url = request.url || 'unknown endpoint';
    const key = `${method} ${url}`;
    const now = Date.now();
    for (const [loggedKey, timestamp] of recentErrorLogs) {
      if (now - timestamp > 30000) recentErrorLogs.delete(loggedKey);
    }
    if (now - (recentErrorLogs.get(key) || 0) > 30000) {
      console.error('[ClassPulse API] Request failed', {
        method,
        url,
        status: error.response?.status || null,
        code: error.code || null,
      });
      recentErrorLogs.set(key, now);
    }
  }
  return Promise.reject(error);
});

export function getStudentConfig(studentId) {
  return { headers: { 'X-Student-ID': studentId } };
}

export function getErrorMessage(error, fallback = 'Something went wrong.') {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.message) return detail.message;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join(' ');
  }
  if (error?.code === 'ECONNABORTED') {
    return 'The server took too long to respond. Try again.';
  }
  if (!error?.response) {
    return 'Cannot reach ClassPulse. Check that the backend is running.';
  }
  return fallback;
}

export default api;
