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
import {
  EmptyState,
  ErrorState,
  LoadingState,
  RefreshNotice,
} from '../components/PageStates';
import Drawer from '../components/ui/Drawer';
import ProgressBar from '../components/ui/ProgressBar';
import StatusPill from '../components/ui/StatusPill';
import Tabs from '../components/ui/Tabs';
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
  ]).then(([diagnoses, summary, assessment]) => ({
    diagnoses,
    summary,
    assessment,
  }));
}
function category(diagnosis) {
  return diagnosis.misconception_code === 'CORRECT'
    ? 'correct'
    : diagnosis.needs_followup ||
        diagnosis.status === 'needs_followup' ||
        diagnosis.misconception_code === 'M06'
      ? 'uncertain'
      : 'likely';
}
function DiagnosisStatus({ diagnosis }) {
  const { t } = useI18n();
  const type = category(diagnosis);
  return (
    <StatusPill
      variant={
        type === 'correct'
          ? 'success'
          : type === 'uncertain'
            ? 'neutral'
            : 'warning'
      }
      icon={
        type === 'correct'
          ? CheckCircle2
          : type === 'uncertain'
            ? CircleHelp
            : AlertTriangle
      }
    >
      {t(
        type === 'correct'
          ? 'correctUnderstanding'
          : type === 'uncertain'
            ? 'uncertainNeedsFollowup'
            : 'likelyDiagnosis',
      )}
    </StatusPill>
  );
}
export default function ClassInsights() {
  const { session } = useDemoSession();
  const { t, language } = useI18n();
  const load = useCallback(
    () => loadInsights(session.classId),
    [session.classId],
  );
  const { data, loading, error, refreshing, reload } = useAsyncData(
    load,
    session.classId,
  );
  const [studentFilter, setStudentFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedId, setSelectedId] = useState(null);
  const students = useMemo(
    () =>
      data
        ? [
            ...new Map(
              data.diagnoses.map((item) => [
                item.student_id,
                item.student_code,
              ]),
            ).entries(),
          ]
            .map(([id, code]) => ({ id, code }))
            .sort((a, b) => a.code.localeCompare(b.code))
        : [],
    [data],
  );
  if (loading) return <LoadingState />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;
  const filtered = data.diagnoses.filter(
    (item) =>
      (!studentFilter || item.student_id === studentFilter) &&
      (statusFilter === 'all' || category(item) === statusFilter),
  );
  const selected = data.diagnoses.find(
    (item) => item.submission_id === selectedId,
  );
  const chartData = Object.entries(data.summary.by_code || {})
    .filter(([code]) => code !== 'CORRECT')
    .map(([code, count]) => ({ code, count }));
  const format = new Intl.NumberFormat(language, { maximumFractionDigits: 10 });
  return (
    <div className="page-content insights-page">
      <RefreshNotice error={error} refreshing={refreshing} onRetry={reload} />
      <PageHeader
        eyebrow={t('classInsights')}
        title={t('insightsTitle')}
        context={session.className}
        description={`${session.subject || ''} · ${session.topic || ''} — ${t('diagnosisHelp')}`}
        actions={
          <span className="observed-badge">
            <BarChart3 size={15} aria-hidden="true" />
            {t('teacherReview')}
          </span>
        }
      />
      <section className="metric-grid metric-grid-three">
        <MetricCard
          label={t('totalDiagnoses')}
          value={data.summary.total_diagnoses}
          icon={BarChart3}
        />
        <MetricCard
          label={t('followupNeeded')}
          value={data.summary.followup_count}
          icon={ArrowUpRight}
        />
        <MetricCard
          label={t('learnersWithDiagnoses')}
          value={students.length}
          icon={UsersRound}
        />
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
            <>
              <div className="chart-container" aria-hidden="true">
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart
                    data={chartData}
                    margin={{ top: 10, right: 12, left: -20, bottom: 0 }}
                  >
                    <CartesianGrid stroke="var(--cp-border)" vertical={false} />
                    <XAxis dataKey="code" axisLine={false} tickLine={false} />
                    <YAxis
                      allowDecimals={false}
                      domain={[0, 'auto']}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip />
                    <Bar
                      dataKey="count"
                      fill="var(--cp-brand)"
                      radius={[4, 4, 0, 0]}
                      isAnimationActive={false}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <dl className="chart-text-alternative">
                {chartData.map((item) => (
                  <div key={item.code}>
                    <dt>{item.code}</dt>
                    <dd>
                      {format.format(item.count)} {t('diagnosedAnswers')}
                    </dd>
                  </div>
                ))}
              </dl>
            </>
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
              <select
                value={studentFilter}
                onChange={(event) => setStudentFilter(event.target.value)}
              >
                <option value="">{t('allStudents')}</option>
                {students.map((student) => (
                  <option key={student.id} value={student.id}>
                    {student.code}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <Tabs
            label={t('diagnosisLegend')}
            value={statusFilter}
            onChange={setStatusFilter}
            items={[
              { value: 'all', label: t('allDiagnoses') },
              { value: 'likely', label: t('likelyDiagnosis') },
              { value: 'uncertain', label: t('followupNeeded') },
              { value: 'correct', label: t('correct') },
            ]}
          >
            {filtered.length ? (
              <div className="diagnosis-records">
                {filtered.map((diagnosis) => (
                  <article
                    className="diagnosis-record"
                    key={diagnosis.submission_id}
                  >
                    <div className="diagnosis-record-heading">
                      <span className="avatar" aria-hidden="true">
                        {diagnosis.student_code.slice(-2)}
                      </span>
                      <strong>{diagnosis.student_code}</strong>
                      <DiagnosisStatus diagnosis={diagnosis} />
                    </div>
                    <div className="diagnosis-meta">
                      <span className="code-pill">
                        {diagnosis.misconception_code}
                      </span>
                      <span>
                        {t('confidence')}:{' '}
                        {diagnosis.confidence == null
                          ? t('notAvailable')
                          : `${format.format(Math.round(diagnosis.confidence * 100))}%`}
                      </span>
                      <span>{diagnosis.provider}</span>
                      <span>
                        {t('diagnosisState', { status: t(diagnosis.status) })}
                      </span>
                    </div>
                    <p>
                      {diagnosis.misconception_description ||
                        diagnosis.evidence ||
                        t('noEvidence')}
                    </p>
                    <button
                      type="button"
                      className="text-link evidence-button"
                      onClick={() => setSelectedId(diagnosis.submission_id)}
                      aria-label={t('viewLearnerEvidence', {
                        student: diagnosis.student_code,
                      })}
                    >
                      {t('viewEvidence')}
                      <ArrowUpRight size={15} aria-hidden="true" />
                    </button>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title={t(
                  data.diagnoses.length ? 'noFilterResults' : 'emptyDiagnoses',
                )}
              />
            )}
          </Tabs>
        </article>
      </section>
      <details className="panel roster-details">
        <summary>
          {t('assessmentProgress')}{' '}
          <span className="count-badge">
            {data.assessment.submitted_students} /{' '}
            {data.assessment.total_students}
          </span>
        </summary>
        <div className="table-scroll">
          <table className="data-table">
            <caption className="sr-only">{t('assessmentProgress')}</caption>
            <thead>
              <tr>
                {[
                  'learner',
                  'status',
                  'answeredQuestions',
                  'diagnosedAnswers',
                  'pendingDiagnoses',
                ].map((key) => (
                  <th scope="col" key={key}>
                    {t(key)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.assessment.students.map((student) => (
                <tr key={student.student_id}>
                  <td data-label={t('learner')}>{student.student_code}</td>
                  <td data-label={t('status')}>
                    <span
                      className={`status-pill ${student.answered_questions ? 'status-completed' : ''}`}
                    >
                      {student.answered_questions
                        ? t('submitted')
                        : t('notStarted')}
                    </span>
                  </td>
                  <td data-label={t('answeredQuestions')}>
                    {student.answered_questions} /{' '}
                    {data.assessment.total_questions_per_student}
                  </td>
                  <td data-label={t('diagnosedAnswers')}>
                    {student.diagnosed_answers}
                  </td>
                  <td data-label={t('pendingDiagnoses')}>
                    {student.pending_diagnoses}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <Drawer
        open={Boolean(selected)}
        onClose={() => setSelectedId(null)}
        title={t('diagnosisEvidence')}
      >
        {selected && (
          <div className="evidence-content">
            <div className="evidence-title">
              <span className="avatar">{selected.student_code.slice(-2)}</span>
              <strong>{selected.student_code}</strong>
              <span className="code-pill">{selected.misconception_code}</span>
            </div>
            <DiagnosisStatus diagnosis={selected} />
            <p className="muted-note">{t('diagnosisHelp')}</p>
            <h3>{t('confidence')}</h3>
            <p>
              {selected.confidence == null
                ? t('notAvailable')
                : `${format.format(Math.round(selected.confidence * 100))}% · ${t(selected.confidence >= 0.75 ? 'confidenceHigh' : selected.confidence >= 0.5 ? 'confidenceModerate' : 'confidenceLow')}`}
            </p>
            {selected.confidence != null && (
              <ProgressBar
                value={selected.confidence * 100}
                label={t('confidence')}
                animated
              />
            )}
            <p className="field-help">{t('confidenceCaution')}</p>
            <h3>{t('evidenceQuote')}</h3>
            <blockquote className="evidence-quote">
              {selected.evidence || t('noEvidence')}
            </blockquote>
            <p className="field-help">{t('responseApiLimit')}</p>
            {selected.misconception_description && (
              <>
                <h3>{t('studentDiagnosis')}</h3>
                <p>{selected.misconception_description}</p>
              </>
            )}
            {selected.misunderstanding_explanation && (
              <>
                <h3>{t('misconceptionExplanation')}</h3>
                <p>{selected.misunderstanding_explanation}</p>
              </>
            )}
            {selected.suggested_intervention && (
              <>
                <h3>{t('suggestedNextStep')}</h3>
                <p>{selected.suggested_intervention}</p>
              </>
            )}
            {selected.followup_question && (
              <div className="notice-inline">
                <CircleHelp size={18} aria-hidden="true" />
                <div>
                  <h3>{t('followupQuestion')}</h3>
                  <p>{selected.followup_question}</p>
                </div>
              </div>
            )}
            <dl className="detail-list">
              <div>
                <dt>{t('provider')}</dt>
                <dd>{selected.provider}</dd>
              </div>
              <div>
                <dt>{t('status')}</dt>
                <dd>{t(selected.status)}</dd>
              </div>
              {selected.model_version && (
                <div>
                  <dt>{t('modelVersion')}</dt>
                  <dd>{selected.model_version}</dd>
                </div>
              )}
            </dl>
          </div>
        )}
      </Drawer>
    </div>
  );
}
