import { LoaderCircle } from 'lucide-react';
export default function Button({
  variant = 'primary',
  size = 'md',
  busy = false,
  disabled = false,
  className = '',
  children,
  type = 'button',
  ...props
}) {
  return (
    <button
      {...props}
      type={type}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={`button button-${variant} button-${size} ${className}`}
    >
      {busy && <LoaderCircle size={17} className="spin" aria-hidden="true" />}
      {children}
    </button>
  );
}
