import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { useId } from 'react';
import useModalDialog from '../../hooks/useModalDialog';
import { useI18n } from '../../i18n/useI18n';
export default function Drawer({
  open,
  onClose,
  title,
  side = 'right',
  children,
  variant = 'drawer',
}) {
  const ref = useModalDialog(open, onClose);
  const titleId = useId();
  const { t } = useI18n();
  return createPortal(
    <dialog
      ref={ref}
      className={`cp-dialog cp-${variant} cp-dialog-${side}`}
      aria-labelledby={titleId}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      {open && (
        <>
          <header className="cp-dialog-header">
            <h2 id={titleId} tabIndex={-1}>
              {title}
            </h2>
            <button
              type="button"
              className="icon-button"
              aria-label={t('close')}
              onClick={onClose}
            >
              <X size={20} aria-hidden="true" />
            </button>
          </header>
          <div className="cp-dialog-body">{children}</div>
        </>
      )}
    </dialog>,
    document.body,
  );
}
