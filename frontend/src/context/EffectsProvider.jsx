import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import EffectsContext from './effectsContext';
import { readCapabilities } from '../hooks/useLiteEffects';
const choices = ['auto', 'lite', 'full'];
const key = 'classpulse-effects';
function readPreference() {
  try {
    const saved = localStorage.getItem(key);
    return choices.includes(saved) ? saved : 'auto';
  } catch {
    return 'auto';
  }
}
export default function EffectsProvider({ children }) {
  const [preference, setValue] = useState(readPreference);
  const [capabilities, setCapabilities] = useState(readCapabilities);
  const lite =
    capabilities.reduced ||
    preference === 'lite' ||
    (preference === 'auto' && capabilities.constrained);
  useLayoutEffect(() => {
    document.documentElement.dataset.effects = lite ? 'lite' : 'full';
  }, [lite]);
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const connection =
      navigator.connection ??
      navigator.mozConnection ??
      navigator.webkitConnection;
    const update = () => setCapabilities(readCapabilities());
    const storage = (e) => {
      if (e.key === key) setValue(readPreference());
    };
    media.addEventListener('change', update);
    connection?.addEventListener?.('change', update);
    window.addEventListener('storage', storage);
    return () => {
      media.removeEventListener('change', update);
      connection?.removeEventListener?.('change', update);
      window.removeEventListener('storage', storage);
    };
  }, []);
  const value = useMemo(
    () => ({
      lite,
      preference,
      reducedMotion: capabilities.reduced,
      setPreference(next) {
        if (!choices.includes(next)) return;
        setValue(next);
        try {
          localStorage.setItem(key, next);
        } catch {
          /* Session preference remains usable. */
        }
      },
    }),
    [lite, preference, capabilities.reduced],
  );
  return (
    <EffectsContext.Provider value={value}>{children}</EffectsContext.Provider>
  );
}
