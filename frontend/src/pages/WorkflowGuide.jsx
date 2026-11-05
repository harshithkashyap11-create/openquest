import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import EffectsControl from '../components/EffectsControl';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import './Learning.css';

export default function WorkflowGuide() {
  const { t } = useI18n();
  const { session } = useDemoSession();
  return <div className="page-content learning-page">
    <PageHeader title={t('mapGuide')} description={t('guideIntro')} />
    {session.role === 'teacher' && <section className="panel"><h2>{t('guideTeacher')}</h2>
      <ol>{['guideStep1', 'guideStep2', 'guideStep3', 'guideStep4'].map(key => <li key={key}>{t(key)}</li>)}</ol>
      <Link to="/teacher/map">{t('mapTitle')}</Link>
    </section>}
    <section className="panel"><h2>{t('guideData')}</h2><p>{t('guideDataText')}</p><p>{t('guideDeviceText')}</p><p>{t('guideLanguage')}</p></section>
    <details className="panel display-preferences"><summary>{t('displayPreferences')}</summary><p>{t('effectsHelp')}</p><EffectsControl /></details>
    <section className="panel"><h2>{t('guideSupport')}</h2><p>{t('guideSupportText')}</p></section>
  </div>;
}
