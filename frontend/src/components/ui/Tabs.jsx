import ActiveIndicator from '../../motion/ActiveIndicator';
import { useId } from 'react';
// Panels stay owned by the caller so tab switches never reset workflow state.
export default function Tabs({ items, value, onChange, label, children }) {
  const id = useId();
  const selected = items.findIndex((item) => item.value === value);
  return (
    <div className="cp-tabs">
      <div
        role="tablist"
        aria-label={label}
        className="cp-tablist"
        onKeyDown={(event) => {
          const offsets = {
            ArrowRight: 1,
            ArrowLeft: -1,
            Home: -selected,
            End: items.length - 1 - selected,
          };
          if (!(event.key in offsets)) return;
          event.preventDefault();
          const next =
            (selected + offsets[event.key] + items.length) % items.length;
          onChange(items[next].value);
          event.currentTarget.querySelectorAll('[role="tab"]')[next]?.focus();
        }}
      >
        <ActiveIndicator value={value} />
        {items.map((item) => (
          <button
            key={item.value}
            id={`${id}-${item.value}`}
            type="button"
            role="tab"
            aria-selected={value === item.value}
            aria-controls={`${id}-panel`}
            tabIndex={value === item.value ? 0 : -1}
            onClick={() => onChange(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div
        id={`${id}-panel`}
        role="tabpanel"
        aria-labelledby={`${id}-${value}`}
      >
        {children}
      </div>
    </div>
  );
}
