import { useContext } from 'react';
import EffectsContext from '../context/effectsContext';
export function useLiteEffects() {
  return useContext(EffectsContext);
}
export function readCapabilities() {
  if (typeof window === 'undefined')
    return { reduced: false, constrained: false };
  const connection =
    navigator.connection ??
    navigator.mozConnection ??
    navigator.webkitConnection;
  return {
    reduced: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    constrained:
      connection?.saveData === true ||
      ['slow-2g', '2g', '3g'].includes(connection?.effectiveType) ||
      (typeof navigator.deviceMemory === 'number' &&
        navigator.deviceMemory <= 4) ||
      (typeof navigator.hardwareConcurrency === 'number' &&
        navigator.hardwareConcurrency <= 4),
  };
}
