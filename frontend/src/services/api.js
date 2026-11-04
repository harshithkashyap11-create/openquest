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
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  try {
    const session = JSON.parse(sessionStorage.getItem('classpulse.demo-session') || 'null');
    if (session) {
      config.headers['X-Demo-Role'] = session.role;
      config.headers['X-Class-ID'] = session.classId;
      if (session.studentId) config.headers['X-Student-ID'] = session.studentId;
      if (session.csrf_token) config.headers['X-CSRF-Token'] = session.csrf_token;
    }
  } catch { /* A corrupt local preference never becomes an authenticated actor. */ }
  return config;
});

const recentErrorLogs = new Map();

api.interceptors.response.use(undefined, (error) => {
  if (error.response?.status === 401 && error.config?.url !== '/auth/login') {
    try {
      const stored = JSON.parse(sessionStorage.getItem('classpulse.demo-session') || 'null');
      if (stored?.authenticated) {
        sessionStorage.removeItem('classpulse.demo-session');
        window.dispatchEvent(new Event('classpulse:session-expired'));
      }
    } catch { /* Keep local queued responses intact during reauthentication. */ }
  }
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
