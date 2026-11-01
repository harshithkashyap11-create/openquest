import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { useI18n } from '../i18n/useI18n';

export default function NotFound() {
  const { t } = useI18n();
  return (
    <main className="entry-page not-found-page">
      <PageHeader title={t('notFoundTitle')} description={t('notFoundDescription')} />
      <Link className="button button-primary" to="/login">{t('backToEntry')}</Link>
    </main>
  );
}
