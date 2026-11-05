import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { LoadingState, ErrorState } from '../components/PageStates';
import { EvidenceState } from '../components/LearningParts';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { classStates } from '../services/learningApi';
import { getClassDiagnoses, getCopilotTaxonomy } from '../services/classpulseApi';
import DiagnosisReview from '../components/DiagnosisReview';
import './Learning.css';

export default function LearningEvidence() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const load = useCallback(() => Promise.all([classStates(session.classId), getClassDiagnoses(session.classId), getCopilotTaxonomy()]), [session.classId]);
  const { data, loading, error, reload } = useAsyncData(load, session.classId);
  const [selectedId, setSelectedId] = useState('');
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const [learners, diagnoses, taxonomy] = data;
  const codes = taxonomy[session.subject]?.find(x => x.topic === session.topic)?.misconceptions || [];
  return <div className="page-content learning-page">
    <PageHeader title={t('learningEvidence')} description={t('evidenceDescription')} />
    <Link className="button button-secondary" to="/teacher/lessons">{t('lessonStudio')}</Link>
    <div className="learning-grid">{learners.filter(x => x.states.length).map(learner => <section key={learner.student_id}>
      <h2>{learner.student_code}</h2>{learner.states.map(s => <div key={`${s.subject}:${s.topic}`}><EvidenceState state={s} />{s.active_misconceptions[0] && <Link className="button button-secondary" to={`/teacher/lessons?code=${encodeURIComponent(s.active_misconceptions[0])}`}>{t('lessonStudio')} · {s.active_misconceptions[0]}</Link>}</div>)}</section>)}</div>
    {!learners.some(x => x.states.length) && <p className="panel">{t('noLearningEvidence')}</p>}
    {diagnoses.length > 0 && <section className="panel"><h2>{t('teacherCorrection')}</h2><p>{t('correctionHelp')}</p>
      <label htmlFor="correction-diagnosis">{t('diagnosis')}</label>
      <select id="correction-diagnosis" className="map-diagnosis-select" value={selectedId || diagnoses[0].id} onChange={e => setSelectedId(e.target.value)}>{diagnoses.map(d => <option key={d.id} value={d.id}>{d.student_code} · {d.misconception_code}</option>)}</select>
      {(() => { const d = diagnoses.find(d => d.id === selectedId) || diagnoses[0]; return <DiagnosisReview key={d.id} diagnosisId={d.id} originalCode={d.misconception_code} codes={codes} onSaved={reload} />; })()}
    </section>}
  </div>;
}
