import ProgressBar from '../components/ui/ProgressBar';
import Score from '../components/ui/ScoreCard';
import { useCallback, useState } from 'react';
import {
  ArrowUpRight,
  CheckCheck,
  ClipboardCheck,
  UsersRound,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import MetricCard from '../components/MetricCard';
import PageHeader from '../components/PageHeader';
import {
  EmptyState,
  ErrorState,
  LoadingState,
  RefreshNotice,
} from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { getErrorMessage } from '../services/api';
import {
  getAssessmentSummary,
  getClassProgress,
  getGroups,
  getDiagnosisSummary,
  runDiagnosis,
} from '../services/classpulseApi';

function loadOverview(classId) {
  return Promise.all([
    getAssessmentSummary(classId),
    getDiagnosisSummary(classId),
    getClassProgress(classId),
    getGroups(classId),
  ]).then(([assessment, diagnoses, progress, groups]) => ({
    assessment,
    diagnoses,
    progress,
    groups,
  }));
}

export default function TeacherDashboard() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const loadOverviewData = useCallback(
    () => loadOverview(session.classId),
    [session.classId],
  );
  const { data, loading, error, refreshing, reload } = useAsyncData(
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
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;

  const { assessment, diagnoses, progress } = data;
  const misconceptionRows = Object.entries(diagnoses.by_code || {})
    .filter(([code]) => code !== 'CORRECT')
    .sort((a, b) => b[1] - a[1]);
  const misconceptionCount = misconceptionRows.reduce(
    (total, [, count]) => total + count,
    0,
  );
  const hasSubmissions = assessment.submitted_students > 0;
  const diagnosisRate = assessment.answered_questions
    ? Math.round(
        (assessment.diagnosed_answers / assessment.answered_questions) * 100,
      )
    : 0;

  return (
    <div className="page-content">
      <RefreshNotice error={error} refreshing={refreshing} onRetry={reload} />
      <PageHeader
        eyebrow={t('dashboardEyebrow')}
        title={t('teacherWelcome')}
        description={`${session.subject || ''} · ${session.topic || ''} — ${t('dashboardDescription')}`}
        context={session.className}
        actions={
          assessment.pending_diagnoses === 0 ? (
            <Link
              className="button button-primary"
              to="/teacher/interventions#groups"
            >
              {t('reviewLearningGroups')}
              <ArrowUpRight size={17} aria-hidden="true" />
            </Link>
          ) : (
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
                    ? t('diagnoseRemaining', {
                        count: assessment.pending_diagnoses,
                      })
                    : t('runDiagnosis')}
            </button>
          )
        }
      />
      {actionMessage && (
        <div
          className="status-message"
          role="status"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '8px',
          }}
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
              {diagnosing
                ? t('loadingShort')
                : t('diagnoseRemaining', {
                    count: assessment.pending_diagnoses,
                  })}
            </button>
          )}
        </div>
      )}
      {actionError && (
        <p className="form-error" role="alert">
          {actionError}
        </p>
      )}

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
              label={t('diagnosedAnswers')}
              value={assessment.diagnosed_answers}
              note={t('teacherReviewNote')}
              icon={CheckCheck}
            />
            <MetricCard
              label={t('followupNeeded')}
              value={diagnoses.followup_count}
              note={t('teacherReviewNote')}
              icon={ArrowUpRight}
            />
          </section>

          <section className="dashboard-grid">
            <article className="panel classroom-snapshot">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">{t('classSnapshot')}</p>
                  <h2>{t('submissionStatus')}</h2>
                </div>
                <Link className="text-link" to="/teacher/insights">
                  {t('viewInsights')}{' '}
                  <ArrowUpRight size={15} aria-hidden="true" />
                </Link>
              </div>
              <div className="progress-summary">
                <div className="progress-labels">
                  <span>{t('diagnosedAnswers')}</span>
                  <strong>{diagnosisRate}%</strong>
                </div>
                <ProgressBar
                  value={diagnosisRate}
                  label={t('diagnosedAnswers')}
                  animated
                />
              </div>
              <dl className="detail-list">
                <div>
                  <dt>{t('submittedStudents')}</dt>
                  <dd>
                    {assessment.submitted_students} /{' '}
                    {assessment.total_students}
                  </dd>
                </div>
                <div>
                  <dt>{t('diagnosedAnswers')}</dt>
                  <dd>{assessment.diagnosed_answers}</dd>
                </div>
                <div>
                  <dt>{t('pendingDiagnoses')}</dt>
                  <dd>{assessment.pending_diagnoses}</dd>
                </div>
                <div>
                  <dt>{t('assessmentQuestions')}</dt>
                  <dd>{assessment.total_questions_per_student}</dd>
                </div>
                <div>
                  <dt>{t('correctUnderstanding')}</dt>
                  <dd>{diagnoses.correct_count}</dd>
                </div>
                <div>
                  <dt>{t('misconceptionCount')}</dt>
                  <dd>{misconceptionCount}</dd>
                </div>
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
                      <ProgressBar
                        value={count}
                        max={Math.max(
                          ...misconceptionRows.map(([, value]) => value),
                        )}
                        label={`${code}: ${count}`}
                        animated
                      />
                      <strong>{count}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title={t('emptyDiagnoses')} />
              )}
            </article>
          </section>

          <section className="panel group-preview-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">{t('loopGroup')}</p>
                <h2>{t('learningGroups')}</h2>
              </div>
              <Link className="text-link" to="/teacher/interventions#groups">
                {t('reviewLearningGroups')}
                <ArrowUpRight size={16} aria-hidden="true" />
              </Link>
            </div>
            {data.groups.length ? (
              <div className="group-preview-list">
                {data.groups.slice(0, 3).map((group) => (
                  <Link
                    className="group-preview"
                    key={group.id}
                    to="/teacher/interventions#groups"
                  >
                    <span className="code-pill">
                      {group.misconception_code}
                    </span>
                    <strong>{group.name}</strong>
                    <span>
                      {group.members.length} {t('members')}
                    </span>
                    <span
                      className={`status-pill status-${group.review_status}`}
                    >
                      {t(group.review_status)}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="muted-note">{t('emptyGroups')}</p>
            )}
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
                  <article
                    className="support-row"
                    key={`${student.student_id}:${student.misconception_code}`}
                  >
                    <div>
                      <strong>{student.student_code}</strong>
                      <span>
                        <span className="code-pill">
                          {student.misconception_code}
                        </span>{' '}
                        {student.reason}
                      </span>
                    </div>
                    <div className="support-score">
                      <strong>
                        {student.followup_accuracy_percentage == null
                          ? t('notAvailable')
                          : `${student.followup_accuracy_percentage}%`}
                      </strong>
                      <small>
                        {student.sample_size} {t('observations')}
                      </small>
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
