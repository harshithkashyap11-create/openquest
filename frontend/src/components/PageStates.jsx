import { AlertCircle, LoaderCircle } from 'lucide-react';
import { getErrorMessage } from '../services/api';
import { useI18n } from '../i18n/useI18n';

export function LoadingState({ label }) {
  const { t } = useI18n();
  return (
    <div className="page-state" role="status" aria-live="polite">
      <LoaderCircle className="spin" size={24} aria-hidden="true" />
      <span>{label || t('loading')}</span>
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  const { t } = useI18n();
  return (
    <div className="page-state page-state-error" role="alert">
      <AlertCircle size={22} aria-hidden="true" />
      <div>
        <strong>{t('errorTitle')}</strong>
        <p>{getErrorMessage(error, t('connectionError'))}</p>
        {onRetry && (
          <button className="button button-secondary" onClick={onRetry}>
            {t('retry')}
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title, children }) {
  return (
    <div className="empty-state">
      <span className="empty-state-mark" aria-hidden="true">
        —
      </span>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </div>
  );
}
