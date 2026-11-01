import { useCallback, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  CircleHelp,
  UsersRound,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import MetricCard from '../components/MetricCard';
import PageHeader from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import {
  getAssessmentSummary,
  getClassDiagnoses,
  getDiagnosisSummary,
} from '../services/classpulseApi';

function loadInsights(classId) {
  return Promise.all([
    getClassDiagnoses(classId),
    getDiagnosisSummary(classId),
    getAssessmentSummary(classId),
  ]).then(
    ([diagnoses, summary, assessment]) => ({ diagnoses, summary, assessment }),
  );
}

export default function ClassInsights() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const loadInsightsData = useCallback(
    () => loadInsights(session.classId),
    [session.classId],
  );
  const { data, loading, error, reload } = useAsyncData(
    loadInsightsData,
    session.classId,
  );
  const [studentFilter, setStudentFilter] = useState('');

  const students = useMemo(() => {
    if (!data) return [];
    return [...new Map(data.diagnoses.map((item) => [item.student_id, item.student_code])).entries()]
      .map(([id, code]) => ({ id, code }))
      .sort((a, b) => a.code.localeCompare(b.code));
  }, [data]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const filtered = studentFilter
    ? data.diagnoses.filter((item) => item.student_id === studentFilter)
    : data.diagnoses;
  const chartData = Object.entries(data.summary.by_code || {})
    .filter(([code]) => code !== 'CORRECT')
    .map(([code, count]) => ({ code, count }));

  return (
    <div className="page-content">
      <PageHeader
        eyebrow={t('classInsights')}
        title={t('insightsTitle')}
        description={`${session.subject || 'Mathematics'} · ${session.topic || 'Fractions'} — ${t('diagnosisHelp')}`}
        actions={<span className="observed-badge"><BarChart3 size={15} /> {t('teacherReview')}</span>}
      />
      <section className="metric-grid metric-grid-three">
        <MetricCard label={t('totalDiagnoses')} value={data.summary.total_diagnoses} icon={BarChart3} />
        <MetricCard label={t('followupNeeded')} value={data.summary.followup_count} icon={ArrowUpRight} />
        <MetricCard label={t('learnersWithDiagnoses')} value={students.length} icon={UsersRound} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('assessment')}</p>
            <h2>{t('assessmentProgress')}</h2>
          </div>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('learner')}</th>
                <th>{t('status')}</th>
                <th>{t('answeredQuestions')}</th>
                <th>{t('diagnosedAnswers')}</th>
                <th>{t('pendingDiagnoses')}</th>
              </tr>
            </thead>
            <tbody>
              {data.assessment.students.map((student) => (
                <tr key={student.student_id}>
                  <td>{student.student_code}</td>
                  <td>
                    <span className={`status-pill ${student.answered_questions ? 'status-completed' : ''}`}>
                      {student.answered_questions ? t('submitted') : t('notStarted')}
                    </span>
                  </td>
                  <td>{student.answered_questions} / {data.assessment.total_questions_per_student}</td>
                  <td>{student.diagnosed_answers}</td>
                  <td>{student.pending_diagnoses}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="insights-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t('misconceptionDistribution')}</p>
              <h2>{t('diagnosisCounts')}</h2>
            </div>
          </div>
          {chartData.length ? (
            <div className="chart-container" role="img" aria-label={t('misconceptionDistribution')}>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} margin={{ top: 10, right: 12, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke="#e9edf4" vertical={false} />
                  <XAxis dataKey="code" axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} axisLine={false} tickLine={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#4d5bd4" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title={t('emptyDiagnoses')} />
          )}
        </article>

        <article className="panel diagnosis-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t('diagnosisDetails')}</p>
              <h2>{t('individualDiagnoses')}</h2>
            </div>
            <label className="filter-field">
              <span className="sr-only">{t('filterStudent')}</span>
              <select value={studentFilter} onChange={(event) => setStudentFilter(event.target.value)}>
                <option value="">{t('allStudents')}</option>
                {students.map((student) => (
                  <option value={student.id} key={student.id}>{student.code}</option>
                ))}
              </select>
            </label>
          </div>
          {filtered.length ? (
            <>
              <div className="diagnosis-legend" aria-label={t('diagnosisLegend')}>
                <span><CheckCircle2 size={15} aria-hidden="true" /> {t('correctUnderstanding')}</span>
                <span><AlertTriangle size={15} aria-hidden="true" /> {t('likelyDiagnosis')}</span>
                <span><CircleHelp size={15} aria-hidden="true" /> {t('uncertainNeedsFollowup')}</span>
              </div>
              <div className="diagnosis-list">
                {filtered.map((diagnosis) => {
                  const isCorrect = diagnosis.misconception_code === 'CORRECT';
                  const isUncertain = diagnosis.needs_followup
                    || diagnosis.status === 'needs_followup'
                    || diagnosis.misconception_code === 'M06';
                  const StatusIcon = isCorrect
                    ? CheckCircle2
                    : isUncertain
                      ? CircleHelp
                      : AlertTriangle;
                  const statusLabel = isCorrect
                    ? t('correctUnderstanding')
                    : isUncertain
                      ? t('uncertainNeedsFollowup')
                      : t('likelyDiagnosis');
                  return (
                    <article
                      className={`diagnosis-item ${isUncertain ? 'diagnosis-uncertain' : ''}`}
                      key={diagnosis.submission_id}
                    >
                  <div className="diagnosis-item-top">
                    <div className="diagnosis-identity">
                      <span className="avatar">{diagnosis.student_code.slice(-2)}</span>
                      <div><strong>{diagnosis.student_code}</strong><small>{t('studentDiagnosis')}</small></div>
                    </div>
                    <span className={`status-pill ${isCorrect ? 'status-correct' : isUncertain ? 'status-uncertain' : 'status-likely'}`}>
                      <StatusIcon size={14} aria-hidden="true" />
                      {statusLabel}
                    </span>
                  </div>
                  <div className="diagnosis-meta">
                    <span className="code-pill">{diagnosis.misconception_code}</span>
                    <span>
                      {t('confidence')}: {Math.round(diagnosis.confidence * 100)}% ·{' '}
                      {diagnosis.confidence >= 0.75
                        ? t('confidenceHigh')
                        : diagnosis.confidence >= 0.5
                          ? t('confidenceModerate')
                          : t('confidenceLow')}
                    </span>
                    <span>{diagnosis.provider}</span>
                  </div>
                  <p className="evidence-quote">{diagnosis.evidence || t('noEvidence')}</p>
                  {diagnosis.misconception_description && (
                    <p>{diagnosis.misconception_description}</p>
                  )}
                  {diagnosis.misunderstanding_explanation && (
                    <p>
                      <strong>{t('misconceptionExplanation')}:</strong>{' '}
                      {diagnosis.misunderstanding_explanation}
                    </p>
                  )}
                  {diagnosis.suggested_intervention && (
                    <p>
                      <strong>{t('suggestedNextStep')}:</strong>{' '}
                      {diagnosis.suggested_intervention}
                    </p>
                  )}
                  {diagnosis.followup_question && (
                    <p className="followup-question"><strong>{t('followupQuestion')}:</strong> {diagnosis.followup_question}</p>
                  )}
                    </article>
                  );
                })}
              </div>
            </>
          ) : (
            <EmptyState title={t('emptyDiagnoses')} />
          )}
        </article>
      </section>
    </div>
  );
}
