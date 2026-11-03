export default function StatusPill({
  variant = 'neutral',
  icon: Icon,
  children,
}) {
  return (
    <span className={`status-pill cp-status-${variant}`}>
      {Icon && <Icon size={14} aria-hidden="true" />}
      {children}
    </span>
  );
}
