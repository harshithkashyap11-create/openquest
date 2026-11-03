import { useLayoutEffect, useRef } from 'react';
import { useLiteEffects } from '../../hooks/useLiteEffects';
import { duration, easing } from '../../motion/presets';
export default function ProgressBar({
  value,
  label,
  max = 100,
  animated = false,
}) {
  const ratio =
    Number.isFinite(value) && max > 0
      ? Math.min(1, Math.max(0, value / max))
      : null;
  const bar = useRef(null);
  const seen = useRef(false);
  const { lite } = useLiteEffects();
  useLayoutEffect(() => {
    if (seen.current || ratio === null) return;
    seen.current = true;
    if (!animated || lite || document.hidden || !bar.current?.animate) return;
    const animation = bar.current.animate(
      [{ transform: 'scaleX(0)' }, { transform: `scaleX(${ratio})` }],
      { duration: duration.chart * 1000, easing: easing.standard },
    );
    return () => animation.cancel();
  }, [ratio, animated, lite]);
  if (ratio === null) return null;
  return (
    <div
      className="cp-progress-track"
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
    >
      <span ref={bar} style={{ transform: `scaleX(${ratio})` }} />
    </div>
  );
}
