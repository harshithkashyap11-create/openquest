import { useCallback, useState } from 'react';
import { ArrowUpRight, CheckCheck, ClipboardCheck, UsersRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import MetricCard from '../components/MetricCard';
import PageHeader from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { getErrorMessage } from '../services/api';
import {
  getAssessmentSummary,
  getClassProgress,
  getDiagnosisSummary,
  runDiagnosis,
} from '../services/classpulseApi';

function loadOverview(classId) {
  return Promise.all([
    getAssessmentSummary(classId),
    getDiagnosisSummary(classId),
    getClassProgress(classId),
  ]).then(([assessment, diagnoses, progress]) => ({ assessment, diagnoses, progress }));
}

export default function TeacherDashboard() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const loadOverviewData = useCallback(
    () => loadOverview(session.classId),
    [session.classId],
  );
  const { data, loading, error, reload } = useAsyncData(
    loadOverviewData,
    session.classId,
  );
  const [diagnosing, setDiagnosing] = useState(false);
  const [actionMessage, setActionMessage] = useState('');
  const [actionError, setActionError] = useState('');

  async function diagnose() {
    setDiagnosing(true);
    setActionMessage('');
    setActionError('');
    try {
      const result = await runDiagnosis(session.classId);
      if (result.remaining_pending > 0) {
        setActionMessage(
          t('diagnosisBatchComplete', {
            count: result.diagnosed,
            remaining: result.remaining_pending,
          }),
        );
      } else {
        setActionMessage(t('diagnosisComplete', { count: result.diagnosed }));
      }
      await reload();
    } catch (requestError) {
      setActionError(getErrorMessage(requestError, t('saveFailed')));
    } finally {
      setDiagnosing(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const { assessment, diagnoses, progress } = data;
  const misconceptionRows = Object.entries(diagnoses.by_code || {})
    .filter(([code]) => code !== 'CORRECT')
    .sort((a, b) => b[1] - a[1]);
  const misconceptionCount = misconceptionRows.reduce((total, [, count]) => total + count, 0);
  const hasSubmissions = assessment.submitted_students > 0;
  const diagnosisRate = assessment.answered_questions
    ? Math.round((assessment.diagnosed_answers / assessment.answered_questions) * 100)
    : 0;

  return (
    <div className="page-content">
      <PageHeader
        eyebrow={t('dashboardEyebrow')}
        title={t('teacherWelcome')}
        description={`${session.subject || 'Mathematics'} · ${session.topic || 'Fractions'} — ${t('dashboardDescription')}`}
        actions={
          <button
            className="button button-primary"
            onClick={diagnose}
            disabled={diagnosing || assessment.pending_diagnoses === 0}
          >
            <ClipboardCheck size={17} aria-hidden="true" />
            {diagnosing
              ? t('loadingShort')
              : assessment.pending_diagnoses === 0
                ? t('allDiagnosed')
                : assessment.diagnosed_answers > 0
                  ? t('diagnoseRemaining', { count: assessment.pending_diagnoses })
                  : t('runDiagnosis')}
          </button>
        }
      />
      {actionMessage && (
        <div
          className="status-message"
          role="status"
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}
        >
          <span>{actionMessage}</span>
          {assessment.pending_diagnoses > 0 && (
            <button
              type="button"
              className="button button-secondary"
              style={{ padding: '4px 10px', fontSize: '0.78rem' }}
              onClick={diagnose}
              disabled={diagnosing}
            >
              <ClipboardCheck size={14} aria-hidden="true" />
              {diagnosing ? t('loadingShort') : t('diagnoseRemaining', { count: assessment.pending_diagnoses })}
            </button>
          )}
        </div>
      )}
      {actionError && <p className="form-error" role="alert">{actionError}</p>}

      {!hasSubmissions ? (
        <>
          <section className="metric-grid" aria-label={t('dashboardTitle')}>
            <MetricCard
              label={t('students')}
              value={assessment.total_students}
              note={t('classRoster')}
              icon={UsersRound}
            />
          </section>
          <section className="panel">
            <EmptyState title={t('noAssessmentsYet')}>
              {t('noAssessmentsExplanation')}
            </EmptyState>
          </section>
        </>
      ) : (
        <>
          <section className="metric-grid" aria-label={t('dashboardTitle')}>
            <MetricCard
              label={t('students')}
              value={assessment.total_students}
              note={t('classRoster')}
              icon={UsersRound}
            />
            <MetricCard
              label={t('submittedStudents')}
              value={`${assessment.submitted_students} / ${assessment.total_students}`}
              note={`${assessment.answered_questions} ${t('answersSubmitted').toLowerCase()}`}
              icon={ClipboardCheck}
            />
            <MetricCard
              label={t('correctUnderstanding')}
              value={diagnoses.correct_count}
              note={t('teacherReviewNote')}
              icon={CheckCheck}
            />
            <MetricCard
              label={t('misconceptionCount')}
              value={misconceptionCount}
              note={t('diagnosedAnswers')}
              icon={ArrowUpRight}
            />
            <MetricCard
              label={t('followupNeeded')}
              value={diagnoses.followup_count}
              note={t('teacherReviewNote')}
              icon={ArrowUpRight}
            />
          </section>

          <section className="dashboard-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t('classSnapshot')}</p>
              <h2>{t('submissionStatus')}</h2>
            </div>
            <Link className="text-link" to="/teacher/insights">
              {t('viewInsights')} <ArrowUpRight size={15} aria-hidden="true" />
            </Link>
          </div>
          <div className="progress-summary">
            <div className="progress-labels">
              <span>{t('diagnosedAnswers')}</span>
              <strong>{diagnosisRate}%</strong>
            </div>
            <div
              className="progress-track"
              role="progressbar"
              aria-label={t('diagnosedAnswers')}
              aria-valuenow={diagnosisRate}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <span style={{ width: `${diagnosisRate}%` }} />
            </div>
          </div>
          <dl className="detail-list">
            <div><dt>{t('submittedStudents')}</dt><dd>{assessment.submitted_students} / {assessment.total_students}</dd></div>
            <div><dt>{t('diagnosedAnswers')}</dt><dd>{assessment.diagnosed_answers}</dd></div>
            <div><dt>{t('pendingDiagnoses')}</dt><dd>{assessment.pending_diagnoses}</dd></div>
            <div><dt>{t('assessmentQuestions')}</dt><dd>{assessment.total_questions_per_student}</dd></div>
          </dl>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t('misconceptionDistribution')}</p>
              <h2>{t('diagnosesReady')}</h2>
            </div>
          </div>
          {misconceptionRows.length ? (
            <div className="distribution-list">
              {misconceptionRows.map(([code, count]) => (
                <div className="distribution-row" key={code}>
                  <span className="code-pill">{code}</span>
                  <div className="distribution-track" aria-hidden="true">
                    <span style={{ width: `${Math.max(4, (count / Math.max(...misconceptionRows.map(([, value]) => value))) * 100)}%` }} />
                  </div>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title={t('emptyDiagnoses')} />
          )}
        </article>
          </section>

          <section className="panel progress-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('progressTitle')}</p>
            <h2>{t('compareScores')}</h2>
          </div>
          <span className="observed-badge">{t('observedScores')}</span>
        </div>
        <div className="score-comparison">
          <Score
            title={t('initialAccuracy')}
            accuracy={progress.initial_assessment.accuracy_percentage}
            correct={progress.initial_assessment.correct_answers}
            sample={progress.initial_assessment.sample_size}
          />
          <div className="score-change">
            <span>{t('accuracyChange')}</span>
            <strong>
              {progress.accuracy_change_percentage_points == null
                ? t('notAvailable')
                : `${progress.accuracy_change_percentage_points > 0 ? '+' : ''}${progress.accuracy_change_percentage_points} pp`}
            </strong>
          </div>
          <Score
            title={t('followupAccuracy')}
            accuracy={progress.followup_assessment.accuracy_percentage}
            correct={progress.followup_assessment.correct_answers}
            sample={progress.followup_assessment.sample_size}
          />
        </div>
        <p className="muted-note">{t('observedOnly')}</p>
          </section>

          <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('followupQueue')}</p>
            <h2>{t('studentsNeedingSupport')}</h2>
          </div>
        </div>
        {progress.students_needing_support.length ? (
          <div className="support-list">
            {progress.students_needing_support.map((student) => (
              <article className="support-row" key={`${student.student_id}:${student.misconception_code}`}>
                <div>
                  <strong>{student.student_code}</strong>
                  <span><span className="code-pill">{student.misconception_code}</span> {student.reason}</span>
                </div>
                <div className="support-score">
                  <strong>
                    {student.followup_accuracy_percentage == null
                      ? t('notAvailable')
                      : `${student.followup_accuracy_percentage}%`}
                  </strong>
                  <small>{student.sample_size} {t('observations')}</small>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title={t('noSupportQueue')} />
        )}
          </section>
        </>
      )}
    </div>
  );
}

function Score({ title, accuracy, correct, sample }) {
  const { t } = useI18n();
  return (
    <div className="score-tile">
      <span>{title}</span>
      <strong>{accuracy == null ? t('notAvailable') : `${accuracy}%`}</strong>
      <small>{correct} / {sample} {t('observations')}</small>
    </div>
  );
}
