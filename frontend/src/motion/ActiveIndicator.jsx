import { useLayoutEffect, useRef } from 'react';
import { useLiteEffects } from '../hooks/useLiteEffects';
import { duration, easing } from './presets';

// A single decorative layer follows the selected control; semantics stay on the controls.
export default function ActiveIndicator({
  value,
  selector = '[aria-selected="true"]',
  className = '',
}) {
  const ref = useRef(null);
  const previous = useRef(null);
  const { lite } = useLiteEffects();
  useLayoutEffect(() => {
    const indicator = ref.current;
    const host = indicator.parentElement;
    const selected = host.querySelector(selector);
    if (!selected) {
      indicator.hidden = true;
      return;
    }
    let animation;
    const update = (animate = false) => {
      const parent = host.getBoundingClientRect();
      const target = selected.getBoundingClientRect();
      const next = {
        x: target.left - parent.left + host.scrollLeft,
        y: target.top - parent.top + host.scrollTop,
        width: target.width,
        height: target.height,
      };
      const old = previous.current;
      if (
        old &&
        Object.keys(next).every((key) => Math.abs(old[key] - next[key]) < 0.5)
      )
        return;
      indicator.hidden = false;
      Object.assign(indicator.style, {
        left: `${next.x}px`,
        top: `${next.y}px`,
        width: `${next.width}px`,
        height: `${next.height}px`,
      });
      animation?.cancel();
      if (
        animate &&
        old &&
        !lite &&
        indicator.animate &&
        next.width &&
        next.height
      ) {
        animation = indicator.animate(
          [
            {
              transform: `translate(${old.x - next.x}px,${old.y - next.y}px) scale(${old.width / next.width},${old.height / next.height})`,
            },
            { transform: 'none' },
          ],
          { duration: duration.standard * 1000, easing: easing.standard },
        );
      }
      previous.current = next;
    };
    update(true);
    const observer = new ResizeObserver(() => update(false));
    observer.observe(host);
    observer.observe(selected);
    return () => {
      observer.disconnect();
      animation?.cancel();
    };
  }, [value, selector, lite]);
  return (
    <span
      ref={ref}
      className={`cp-active-indicator ${className}`}
      aria-hidden="true"
    />
  );
}
