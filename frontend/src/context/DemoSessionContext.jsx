import { useEffect, useMemo, useState } from 'react';
import DemoSessionContext from './demoSessionContext';
import api from '../services/api';
import { classDisplayName } from '../services/classDisplayName';

const STORAGE_KEY = 'classpulse.demo-session';

function readSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
    return session ? { ...session, className: classDisplayName(session.className, session.topic) } : null;
  } catch {
    return null;
  }
}

function writeSession(session) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch (error) {
    console.error('[ClassPulse demo] Could not persist demo session', error);
  }
}

function clearStoredSession() {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('[ClassPulse demo] Could not clear demo session', error);
  }
}

export function DemoSessionProvider({ children }) {
  const [session, setSession] = useState(readSession);
  useEffect(() => {
    const expired = () => setSession(null);
    window.addEventListener('classpulse:session-expired', expired);
    return () => window.removeEventListener('classpulse:session-expired', expired);
  }, []);
  const value = useMemo(
    () => ({
      session,
      startSession(nextSession) {
        const displaySession = { ...nextSession, className: classDisplayName(nextSession.className, nextSession.topic) };
        writeSession(displaySession);
        setSession(displaySession);
      },
      async endSession() {
        const { assertOfflineCanLogout, clearOfflineData } = await import('../services/offlineLearning');
        await assertOfflineCanLogout();
        if (session?.authenticated) await api.post('/auth/logout');
        await clearOfflineData();
        clearStoredSession();
        setSession(null);
      },
    }),
    [session],
  );
  return (
    <DemoSessionContext.Provider value={value}>
      {children}
    </DemoSessionContext.Provider>
  );
}
