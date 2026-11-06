import { ArrowRight, BookOpenCheck, ClipboardList } from 'lucide-react';
import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import StudentWork from '../components/StudentWork';
import { JourneyNavigation } from '../components/StudentJourney';
import {
  EmptyState,
  ErrorState,
  LoadingState,
  RefreshNotice,
} from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import {
  getClassAssessment,
  getStudentInterventions,
} from '../services/classpulseApi';

function loadStudentHome(classId, studentId) {
  return Promise.all([
    getClassAssessment(classId, studentId),
    getStudentInterventions(studentId),
  ]).then(([assessment, assignments]) => ({ assessment, assignments }));
}

export default function StudentDashboard() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const loadHome = useCallback(
    () => loadStudentHome(session.classId, session.studentId),
    [session.classId, session.studentId],
  );
  const { data, loading, error, refreshing, reload } = useAsyncData(
    loadHome,
    `${session.classId}:${session.studentId}`,
  );

  if (loading) return <LoadingState />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;

  const openAssignments = data.assignments.filter(
    (item) => item.status !== 'completed',
  );
  const completedAssignments = data.assignments.filter(
    (item) => item.status === 'completed',
  );

  return (
    <div className="page-content">
      <RefreshNotice error={error} refreshing={refreshing} onRetry={reload} />
      <PageHeader
        eyebrow={t('studentView')}
        title={`${t('studentGreeting')}, ${session.studentCode}`}
        description={`${session.subject || 'Mathematics'} · ${session.topic || 'Fractions'} — ${t('homeDescription')}`}
      />
      <JourneyNavigation />
      {data.assessment.questions.length ? (
        <section className="student-welcome-card">
          <div className="welcome-icon">
            <BookOpenCheck size={23} aria-hidden="true" />
          </div>
          <div style={{ flex: 1 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '4px',
              }}
            >
              <p className="eyebrow" style={{ margin: 0 }}>
                {data.assessment.attempt_count === 0
                  ? t('assessmentNotStarted')
                  : data.assessment.attempt_count === 1
                    ? t('assessmentSubmitted')
                    : t('previousAttemptsAvailable', {
                        count: data.assessment.attempt_count,
                      })}
              </p>
              <span
                className={`status-pill ${data.assessment.attempt_count ? 'status-completed' : 'status-assigned'}`}
              >
                {data.assessment.attempt_count === 0
                  ? t('notStarted')
                  : data.assessment.attempt_count === 1
                    ? t('submitted')
                    : `${data.assessment.attempt_count} ${t('attempts')}`}
              </span>
            </div>
            <h2>{data.assessment.title}</h2>
            <p>
              {data.assessment.attempt_count === 0
                ? `${data.assessment.questions.length} ${t('questions')} · ${data.assessment.topic}`
                : data.assessment.attempt_count === 1
                  ? t('assessmentAttemptCompleted', {
                      attempt: data.assessment.latest_attempt_no || 1,
                    })
                  : `${data.assessment.questions.length} ${t('questions')} · ${t('assessmentAvailable')}`}
            </p>
          </div>
          <Link to="/student/assessment" className="button button-primary">
            {data.assessment.attempt_count === 0
              ? t('startAssessment')
              : t('takeAnotherAttempt')}{' '}
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </section>
      ) : (
        <section className="panel">
          <EmptyState title={t('noAssessmentQuestions')} />
        </section>
      )}

      <StudentWork studentId={session.studentId} />

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('keepLearning')}</p>
            <h2>{t('assignedActivities')}</h2>
          </div>
          <span className="count-badge">
            {openAssignments.length} {t('active')}
          </span>
        </div>
        {openAssignments.length ? (
          <div className="student-activity-grid">
            {openAssignments.map((assignment) => (
              <article className="student-activity-card" key={assignment.id}>
                <div className="diagnosis-meta">
                  <span className="code-pill">
                    {assignment.intervention.misconception_code}
                  </span>
                  <span className={`status-pill status-${assignment.status}`}>
                    {t(assignment.status)}
                  </span>
                </div>
                <h3>{assignment.intervention.title}</h3>
                <p>{assignment.intervention.learning_objective}</p>
                <Link
                  to={`/student/interventions/${assignment.id}`}
                  className="text-link"
                >
                  {t('openActivity')}{' '}
                  <ArrowRight size={15} aria-hidden="true" />
                </Link>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title={t('noStudentActivities')} />
        )}
      </section>

      {completedAssignments.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t('completedInterventions')}</p>
              <h2>{t('recentlyCompleted')}</h2>
            </div>
            <ClipboardList size={18} aria-hidden="true" />
          </div>
          <div className="completed-list">
            {completedAssignments.map((assignment) => (
              <Link
                to={`/student/interventions/${assignment.id}`}
                key={assignment.id}
              >
                <span>{assignment.intervention.title}</span>
                <span className="status-pill status-completed">
                  {t('completed')}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
