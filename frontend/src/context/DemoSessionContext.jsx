import { useMemo, useState } from 'react';
import DemoSessionContext from './demoSessionContext';

const STORAGE_KEY = 'classpulse.demo-session';

function readSession() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
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
  const value = useMemo(
    () => ({
      session,
      startSession(nextSession) {
        writeSession(nextSession);
        setSession(nextSession);
      },
      endSession() {
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
