// Fluid Precision. Seconds here, milliseconds in the CSS token sheet.
export const duration = Object.freeze({
  instant: 0,
  fast: 0.12,
  status: 0.16,
  standard: 0.2,
  page: 0.26,
  modal: 0.28,
  drawer: 0.32,
  toast: 0.22,
  chart: 0.48,
  count: 0.6,
});
export const easing = Object.freeze({
  standard: 'cubic-bezier(0.2,0,0,1)',
  enter: 'cubic-bezier(0.16,1,0.3,1)',
  exit: 'cubic-bezier(0.4,0,1,1)',
});
export const spring = Object.freeze({
  gentle: { stiffness: 280, damping: 30, mass: 1 },
  responsive: { stiffness: 420, damping: 34, mass: 0.8 },
  drawer: { stiffness: 350, damping: 36, mass: 1 },
  modal: { stiffness: 320, damping: 30, mass: 0.9 },
  indicator: { stiffness: 480, damping: 40, mass: 0.7 },
});
export const stagger = Object.freeze({
  itemDelay: 0.035,
  maximumItems: 8,
  maximumSequence: 0.65,
});
export function routeFrames(direction = 'sibling') {
  const transform =
    direction === 'forward'
      ? 'translateX(24px)'
      : direction === 'backward'
        ? 'translateX(-24px)'
        : 'translateY(8px)';
  return [
    { opacity: 0, transform },
    { opacity: 1, transform: 'none' },
  ];
}
export function navigationDirection(previous, next, type, historyDelta = 0) {
  if (!previous || previous === next) return 'none';
  if (type === 'POP' && historyDelta)
    return historyDelta < 0 ? 'backward' : 'forward';
  if (next.endsWith('/progress') || previous.endsWith('/progress'))
    return 'sibling';
  const depth = (path) =>
    path.endsWith('/overview') || path.endsWith('/dashboard')
      ? 0
      : path.split('/').filter(Boolean).length;
  return depth(next) > depth(previous)
    ? 'forward'
    : depth(next) < depth(previous)
      ? 'backward'
      : 'sibling';
}
