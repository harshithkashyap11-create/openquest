import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { LoadingState, ErrorState } from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import api from '../services/api';
import './Learning.css';

export default function WorkflowGuide() {
  const { t, language } = useI18n();
  const { session } = useDemoSession();
  const load = useCallback(async () => (await api.get('/system-status')).data, []);
  const { data, loading, error, reload, refreshing } = useAsyncData(load, 'system-status');
  return <div className="page-content learning-page">
    <PageHeader title={t('mapGuide')} description={t('guideIntro')} />
    {session.role === 'teacher' && <section className="panel"><h2>{t('guideTeacher')}</h2>
      <ol>{['guideStep1', 'guideStep2', 'guideStep3', 'guideStep4'].map(key => <li key={key}>{t(key)}</li>)}</ol>
      <Link to="/teacher/map">{t('mapTitle')}</Link>
    </section>}
    <section className="panel"><h2>{t('guideData')}</h2><p>{t('guideDataText')}</p><p>{t('guideDeviceText')}</p><p>{t('guideLanguage')}</p></section>
    <section className="panel"><h2>{t('guideStatus')}</h2><p>{t('guideStatusHelp')}</p>
      {loading ? <LoadingState /> : error ? <ErrorState error={error} message={t('mapLoadFailed')} onRetry={reload} /> : <>
        <dl><dt>{t('guideApp')}</dt><dd>{t(`guideStatus_${data.app}`)}</dd>
          <dt>{t('guideDatabase')}</dt><dd>{t(`guideStatus_${data.database}`)}</dd>
          <dt>{t('guideAI')}</dt><dd>{t(`guideStatus_${data.ai_provider}`)} · {t('guideReachability')}</dd></dl>
        <p>{new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(data.checked_at))}</p>
      </>}
      <button className="button button-secondary" disabled={refreshing} onClick={reload}>{t('refresh')}</button>
    </section>
    <section className="panel"><h2>{t('guideSupport')}</h2><p>{t('guideSupportText')}</p></section>
  </div>;
}
