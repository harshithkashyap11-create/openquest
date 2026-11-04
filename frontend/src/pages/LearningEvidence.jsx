import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { LoadingState, ErrorState } from '../components/PageStates';
import { EvidenceState } from '../components/LearningParts';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { classStates, corrections, correctDiagnosis } from '../services/learningApi';
import { getClassDiagnoses, getCopilotTaxonomy } from '../services/classpulseApi';
import { getErrorMessage } from '../services/api';
import './Learning.css';

export default function LearningEvidence() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const load = useCallback(() => Promise.all([classStates(session.classId), getClassDiagnoses(session.classId), getCopilotTaxonomy()]), [session.classId]);
  const { data, loading, error, reload } = useAsyncData(load, session.classId);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const [learners, diagnoses, taxonomy] = data;
  const codes = taxonomy[session.subject]?.find(x => x.topic === session.topic)?.misconceptions || [];
  async function submit(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    const form = new FormData(event.currentTarget);
    try {
      const id = form.get('diagnosis');
      const history = await corrections(id);
      await correctDiagnosis(id, { code: form.get('code'), reason: form.get('reason'), expected_version: history.at(-1)?.version || 0, request_id: crypto.randomUUID() });
      setMessage(t('correctionSaved')); await reload();
    } catch (e) { setMessage(getErrorMessage(e)); }
    finally { setBusy(false); }
  }
  return <div className="page-content learning-page">
    <PageHeader title={t('learningEvidence')} description={t('evidenceDescription')} />
    <Link className="button button-secondary" to="/teacher/lessons">{t('lessonStudio')}</Link>
    <div className="learning-grid">{learners.filter(x => x.states.length).map(learner => <section key={learner.student_id}>
      <h2>{learner.student_code}</h2>{learner.states.map(s => <div key={`${s.subject}:${s.topic}`}><EvidenceState state={s} />{s.active_misconceptions[0] && <Link className="button button-secondary" to={`/teacher/lessons?code=${encodeURIComponent(s.active_misconceptions[0])}`}>{t('lessonStudio')} · {s.active_misconceptions[0]}</Link>}</div>)}</section>)}</div>
    {!learners.some(x => x.states.length) && <p className="panel">{t('noLearningEvidence')}</p>}
    {diagnoses.length > 0 && <section className="panel"><h2>{t('teacherCorrection')}</h2><p>{t('correctionHelp')}</p>
      <form className="learning-form" onSubmit={submit}>
        <label htmlFor="correction-diagnosis">{t('diagnosis')}</label><select id="correction-diagnosis" name="diagnosis" required>{diagnoses.map(d => <option key={d.id} value={d.id}>{d.student_code} · {d.misconception_code} · {d.evidence.slice(0, 60)}</option>)}</select>
        <label htmlFor="correction-code">{t('misconception')}</label><select id="correction-code" name="code"><option value="CORRECT">CORRECT</option>{codes.map(c => <option key={c.code} value={c.code}>{c.code} · {c.category}</option>)}</select>
        <label htmlFor="correction-reason">{t('reviewReason')}</label><textarea id="correction-reason" name="reason" minLength={5} maxLength={1000} required />
        <button className="button button-primary" disabled={busy}>{t('saveCorrection')}</button>
      </form></section>}
    {message && <p role="status" className="panel">{message}</p>}
  </div>;
}
