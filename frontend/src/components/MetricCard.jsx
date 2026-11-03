import { useLayoutEffect, useRef } from 'react';
import Card from './ui/Card';
import { useLiteEffects } from '../hooks/useLiteEffects';
import { useI18n } from '../i18n/useI18n';
import { duration } from '../motion/presets';
export default function MetricCard({ label, value, note, icon: Icon }) {
  const count = useRef(null);
  const { lite } = useLiteEffects();
  const { t, language } = useI18n();
  const shown =
    value == null
      ? t('notAvailable')
      : typeof value === 'number'
        ? new Intl.NumberFormat(language, { maximumFractionDigits: 10 }).format(
            value,
          )
        : value;
  const first = useRef(true);
  useLayoutEffect(() => {
    if (!first.current) return;
    first.current = false;
    if (
      lite ||
      typeof value !== 'number' ||
      !Number.isInteger(value) ||
      document.hidden
    )
      return;
    const element = count.current;
    let frame;
    const start = performance.now();
    const tick = (now) => {
      const elapsed = Math.min(1, (now - start) / (duration.count * 1000));
      element.textContent = new Intl.NumberFormat(language).format(
        Math.round(value * (1 - Math.pow(1 - elapsed, 3))),
      );
      if (elapsed < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      element.textContent = shown;
    };
  }, [lite, value, shown, language]);
  return (
    <Card className="metric-card">
      <div className="metric-topline">
        <span>{label}</span>
        {Icon && (
          <span className="metric-icon">
            <Icon size={19} aria-hidden="true" />
          </span>
        )}
      </div>
      <strong className="metric-value">
        <span className="sr-only">{shown}</span>
        <span aria-hidden="true" ref={count}>
          {shown}
        </span>
      </strong>
      {note && <span className="metric-note">{note}</span>}
    </Card>
  );
}
