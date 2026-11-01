import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, Check, CircleAlert, UsersRound } from 'lucide-react';
import { Link, useLocation, useParams } from 'react-router-dom';
import MetricCard from '../components/MetricCard';
import PageHeader from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { getErrorMessage } from '../services/api';
import {
  completeIntervention,
  generateGroups,
  generateIntervention,
  getClassAssignments,
  getGroups,
  getStudentAssignment,
  getStudentInterventions,
  getStudentReassessment,
  reviewGroup,
  submitPractice,
  submitReassessment,
} from '../services/classpulseApi';

function loadTeacherInterventions(classId) {
  return Promise.all([getGroups(classId), getClassAssignments(classId)]).then(
    ([groups, assignments]) => ({ groups, assignments }),
  );
}

export default function Intervention() {
  const { session } = useDemoSession();
  const { assignmentId } = useParams();
  if (session.role === 'student' && assignmentId) {
    return <StudentActivity assignmentId={assignmentId} studentId={session.studentId} />;
  }
  if (session.role === 'student') return <StudentActivityList studentId={session.studentId} />;
  return <TeacherInterventions classId={session.classId} />;
}

function TeacherInterventions({ classId }) {
  const { t } = useI18n();
  const location = useLocation();
  const loadTeacherData = useCallback(
    () => loadTeacherInterventions(classId),
    [classId],
  );
  const { data, loading, error, reload } = useAsyncData(
    loadTeacherData,
    classId,
  );
  const [working, setWorking] = useState('');
  const [message, setMessage] = useState('');
  const [actionError, setActionError] = useState('');
  const [generatedIntervention, setGeneratedIntervention] = useState(null);

  useEffect(() => {
    if (location.hash) {
      document.getElementById(location.hash.slice(1))?.scrollIntoView();
    }
  }, [location.hash, data]);

  async function perform(id, action, callback) {
    setWorking(id);
    setMessage('');
    setActionError('');
    try {
      const result = await callback();
      if (action === 'generate') {
        setGeneratedIntervention(result.intervention);
        setMessage(t('interventionGenerated', { count: result.assignments_created }));
      } else {
        setMessage(action === 'groups' ? t('groupsGenerated') : t('groupReviewed'));
      }
      await reload();
    } catch (requestError) {
      setActionError(getErrorMessage(requestError, t('saveFailed')));
    } finally {
      setWorking('');
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const approvedGroups = data.groups.filter((group) => group.teacher_approved);
  const activeAssignments = data.assignments.filter((item) => item.status !== 'completed').length;
  const completedAssignments = data.assignments.length - activeAssignments;

  return (
    <div className="page-content">
      <PageHeader
        eyebrow={t('interventions')}
        title={t('interventionManagement')}
        description={t('groupsAndReview')}
        actions={
          <button
            className="button button-primary"
            disabled={Boolean(working)}
            onClick={() => perform('groups', 'groups', () => generateGroups(classId))}
          >
            <UsersRound size={17} aria-hidden="true" />
            {working === 'groups' ? t('loadingShort') : t('generateGroups')}
          </button>
        }
      />
      {message && <p className="status-message" role="status">{message}</p>}
      {actionError && <p className="form-error" role="alert">{actionError}</p>}

      <section className="metric-grid metric-grid-three">
        <MetricCard label={t('learningGroups')} value={data.groups.length} icon={UsersRound} />
        <MetricCard label={t('activeAssignments')} value={activeAssignments} />
        <MetricCard label={t('completedInterventions')} value={completedAssignments} />
      </section>

      <section className="panel">
        <div id="groups" />
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('groupActions')}</p>
            <h2>{t('groupsTitle')}</h2>
          </div>
        </div>
        {data.groups.length ? (
          <div className="group-list">
            {data.groups.map((group) => (
              <article className="group-card" key={group.id}>
                <div className="group-card-main">
                  <div className="group-heading">
                    <span className="code-pill">{group.misconception_code}</span>
                    <span className={`status-pill status-${group.review_status}`}>{t(group.review_status)}</span>
                  </div>
                  <h3>{group.name}</h3>
                  <p>{group.members.length} {t('members').toLowerCase()} · {group.topic}</p>
                  <div className="member-codes">
                    {group.members.map((member) => <span key={member.student_id}>{member.student_code}</span>)}
                  </div>
                </div>
                <div className="group-actions">
                  {group.review_status === 'proposed' ? (
                    <>
                      <button
                        className="button button-secondary"
                        disabled={Boolean(working)}
                        onClick={() => perform(group.id, 'review', () => reviewGroup(group.id, 'rejected'))}
                      >
                        {t('reject')}
                      </button>
                      <button
                        className="button button-primary"
                        disabled={Boolean(working)}
                        onClick={() => perform(group.id, 'review', () => reviewGroup(group.id, 'approved'))}
                      >
                        <Check size={16} aria-hidden="true" /> {t('approve')}
                      </button>
                    </>
                  ) : group.teacher_approved ? (
                    <button
                      className="button button-primary"
                      disabled={Boolean(working)}
                      onClick={() => perform(group.id, 'generate', () => generateIntervention(group.id))}
                    >
                      {working === group.id ? t('loadingShort') : t('generateIntervention')}
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title={t('emptyGroups')} />
        )}
        {approvedGroups.some((group) => group.misconception_code === 'M06') && (
          <p className="notice-inline"><CircleAlert size={16} /> {t('m06Notice')}</p>
        )}
      </section>

      {generatedIntervention && (
        <section className="panel generated-intervention" aria-live="polite">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{t('generatedIntervention')}</p>
              <h2>{generatedIntervention.title}</h2>
            </div>
            {generatedIntervention.provider && (
              <span className="observed-badge">
                {generatedIntervention.provider.toLowerCase() === 'template'
                  ? t('templateFallback')
                  : generatedIntervention.provider.toLowerCase() === 'openrouter'
                    ? t('personalizedWithOpenRouter')
                    : generatedIntervention.provider.toLowerCase() === 'gemini'
                      ? t('generatedWithGemini')
                      : t('personalizedWithProvider', { provider: generatedIntervention.provider })}
              </span>
            )}
          </div>
          <p><strong>{t('learningObjective')}:</strong> {generatedIntervention.learning_objective}</p>
          <p className="learning-explanation">{generatedIntervention.explanation}</p>
          {generatedIntervention.generation_note && (
            <p className="muted-note">{generatedIntervention.generation_note}</p>
          )}
          {generatedIntervention.expected_answers?.length > 0 && (
            <details className="result-details teacher-answer-key">
              <summary>{t('teacherAnswerKey')}</summary>
              <ol>
                {generatedIntervention.expected_answers.map((answer, index) => (
                  <li key={`${index}:${answer}`}>{answer}</li>
                ))}
              </ol>
            </details>
          )}
        </section>
      )}

      <section className="panel">
        <div id="assignments" />
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('assignmentTracking')}</p>
            <h2>{t('reassessmentResults')}</h2>
          </div>
        </div>
        {data.assignments.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('learner')}</th>
                  <th>{t('activity')}</th>
                  <th>{t('status')}</th>
                  <th>{t('reassessmentScore')}</th>
                  <th>{t('sampleSize')}</th>
                  <th>{t('reassessmentResults')}</th>
                </tr>
              </thead>
              <tbody>
                {data.assignments.map((item) => (
                  <tr key={item.assignment_id}>
                    <td>{item.student_code}</td>
                    <td><span className="code-pill">{item.misconception_code}</span> {item.title}</td>
                    <td><span className={`status-pill status-${item.status}`}>{t(item.status)}</span></td>
                    <td>{item.reassessment_accuracy_percentage == null ? t('noReassessment') : `${item.reassessment_accuracy_percentage}%`}</td>
                    <td>{item.reassessment_total_questions ?? '—'}</td>
                    <td>
                      {item.reassessment_results.length ? (
                        <details className="result-details">
                          <summary>{t('viewAnswers')}</summary>
                          <div>
                            {item.reassessment_results.map((result) => (
                              <p key={result.question_id}>
                                <strong>{result.is_correct ? t('correct') : t('incorrect')}:</strong>{' '}
                                {result.question_text} — {result.answer || t('noAnswer')}
                              </p>
                            ))}
                          </div>
                        </details>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title={t('emptyAssignments')} />
        )}
      </section>
    </div>
  );
}

function StudentActivityList({ studentId }) {
  const { t } = useI18n();
  const loadStudentAssignments = useCallback(
    () => getStudentInterventions(studentId),
    [studentId],
  );
  const { data: assignments, loading, error, reload } = useAsyncData(
    loadStudentAssignments,
    studentId,
  );
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="page-content">
      <PageHeader eyebrow={t('interventions')} title={t('assignedActivities')} />
      {assignments.length ? (
        <div className="student-activity-grid">
          {assignments.map((item) => (
            <article className="student-activity-card" key={item.id}>
              <div className="diagnosis-meta">
                <span className="code-pill">{item.intervention.misconception_code}</span>
                <span className={`status-pill status-${item.status}`}>{t(item.status)}</span>
              </div>
              <h2>{item.intervention.title}</h2>
              <p>{item.intervention.learning_objective}</p>
              <Link className="button button-primary" to={`/student/interventions/${item.id}`}>
                {t('openActivity')} <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title={t('noStudentActivities')} />
      )}
    </div>
  );
}

function StudentActivity({ assignmentId, studentId }) {
  const { t } = useI18n();
  const loadAssignment = useCallback(
    () => getStudentAssignment(assignmentId, studentId),
    [assignmentId, studentId],
  );
  const { data, loading, error, reload } = useAsyncData(
    loadAssignment,
    `${assignmentId}:${studentId}`,
  );
  const [practiceAnswers, setPracticeAnswers] = useState({});
  const [practiceResult, setPracticeResult] = useState(null);
  const [reassessment, setReassessment] = useState(null);
  const [reassessmentAnswers, setReassessmentAnswers] = useState({});
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState('');
  const [completed, setCompleted] = useState(false);
  const [prevAssignmentId, setPrevAssignmentId] = useState(null);

  if (data && prevAssignmentId !== data.id) {
    setPrevAssignmentId(data.id);
    if (data.practice_responses?.length) {
      const restored = {};
      const results = [];
      for (const item of data.practice_responses) {
        restored[item.question_index] = item.answer || '';
        results.push({
          question_index: item.question_index,
          is_correct: item.is_correct,
        });
      }
      setPracticeAnswers(restored);
      setPracticeResult({
        correct_answers: results.filter((r) => r.is_correct).length,
        incorrect_answers: results.filter((r) => !r.is_correct).length,
        results,
      });
    }
  }

  useEffect(() => {
    if (data?.status === 'completed') {
      getStudentReassessment(data.id, studentId)
        .then((quiz) => {
          setReassessment(quiz);
          if (quiz.results?.length) {
            const ansMap = {};
            for (const r of quiz.results) {
              ansMap[r.question_id] = r.answer || '';
            }
            setReassessmentAnswers(ansMap);
          }
        })
        .catch((loadErr) => {
          console.error('[ClassPulse] Failed to auto-restore reassessment', loadErr);
        });
    }
  }, [data, studentId]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const assignment = data;
  const intervention = assignment.intervention;

  async function checkPractice(event) {
    event.preventDefault();
    setActionError('');
    setBusy('practice');
    try {
      const result = await submitPractice(
        assignmentId,
        studentId,
        intervention.practice_questions.map((question) => ({
          question_index: question.question_index,
          answer: practiceAnswers[question.question_index] || '',
        })),
      );
      setPracticeResult(result);
    } catch (requestError) {
      setActionError(getErrorMessage(requestError, t('saveFailed')));
    } finally {
      setBusy('');
    }
  }

  async function finishActivity() {
    setActionError('');
    setBusy('complete');
    try {
      const result = await completeIntervention(assignmentId, studentId);
      setReassessment(result.reassessment);
      setCompleted(true);
    } catch (requestError) {
      setActionError(getErrorMessage(requestError, t('saveFailed')));
    } finally {
      setBusy('');
    }
  }

  async function openReassessment() {
    setActionError('');
    setBusy('reassessment');
    try {
      const quiz = await getStudentReassessment(assignmentId, studentId);
      setReassessment(quiz);
      if (quiz.results?.length) {
        const ansMap = {};
        for (const r of quiz.results) {
          ansMap[r.question_id] = r.answer || '';
        }
        setReassessmentAnswers(ansMap);
      }
    } catch (requestError) {
      setActionError(getErrorMessage(requestError, t('saveFailed')));
    } finally {
      setBusy('');
    }
  }

  async function sendReassessment(event) {
    event.preventDefault();
    setActionError('');
    setBusy('submit-reassessment');
    try {
      const result = await submitReassessment(
        reassessment.id,
        studentId,
        reassessment.questions.map((question) => ({
          question_id: question.id,
          answer: reassessmentAnswers[question.id] || '',
        })),
      );
      setReassessment(result);
      if (result.results?.length) {
        const ansMap = {};
        for (const r of result.results) {
          ansMap[r.question_id] = r.answer || '';
        }
        setReassessmentAnswers(ansMap);
      }
    } catch (requestError) {
      setActionError(requestError?.response?.data?.detail || t('saveFailed'));
    } finally {
      setBusy('');
    }
  }

  const practiceChecked = practiceResult !== null;
  const reassessmentDone = reassessment?.status === 'completed';

  return (
    <div className="page-content activity-content">
      <PageHeader
        eyebrow={`${intervention.misconception_code} · ${t('targetedPractice')}`}
        title={intervention.title}
        description={intervention.introduction}
      />
      {actionError && <p className="form-error" role="alert">{actionError}</p>}

      <section className="activity-layout">
        <div className="activity-main">
          <article className="panel learning-panel">
            <p className="eyebrow">{t('learningObjective')}</p>
            <h2>{intervention.learning_objective}</h2>
            <p className="learning-explanation">{intervention.explanation}</p>
            <div className="example-box">
              <p className="eyebrow">{t('guidedExample')}</p>
              <strong>{intervention.guided_example.question}</strong>
              <p>{intervention.guided_example.steps}</p>
              <p className="example-answer">
                <strong>{t('expectedAnswer')}:</strong> {intervention.guided_example.answer}
              </p>
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div><p className="eyebrow">{t('practice')}</p><h2>{t('activityInstructions')}</h2></div>
            </div>
            <p className="body-copy">{intervention.instructions}</p>
            <form onSubmit={checkPractice}>
              <div className="question-stack">
                {intervention.practice_questions.map((question, index) => {
                  const result = practiceResult?.results.find((item) => item.question_index === question.question_index);
                  return (
                    <div className="practice-question" key={question.question_index}>
                      <label htmlFor={`practice-${question.question_index}`}>
                        <span className="question-number">{index + 1}</span> {question.question}
                      </label>
                      <input
                        id={`practice-${question.question_index}`}
                        value={practiceAnswers[question.question_index] || ''}
                        onChange={(event) => setPracticeAnswers((answers) => ({
                          ...answers,
                          [question.question_index]: event.target.value,
                        }))}
                        placeholder={t('answerPlaceholder')}
                        disabled={practiceChecked || assignment.status === 'completed'}
                        required
                      />
                      <span className="field-help">{question.hint}</span>
                      {result && (
                        <span className={result.is_correct ? 'answer-feedback correct' : 'answer-feedback incorrect'}>
                          {result.is_correct ? t('correct') : t('incorrect')}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
              {!practiceChecked && assignment.status !== 'completed' && (
                <button className="button button-secondary" disabled={Boolean(busy)}>
                  {busy === 'practice' ? t('loadingShort') : t('submitPractice')}
                </button>
              )}
            </form>
          </article>

          {practiceResult && (
            <p className="status-message" role="status">
              {t('practiceScore', {
                correct: practiceResult.correct_answers,
                total: practiceResult.correct_answers + practiceResult.incorrect_answers,
              })}
            </p>
          )}

          {!reassessment && assignment.status !== 'completed' && practiceChecked && (
            <button className="button button-primary" onClick={finishActivity} disabled={Boolean(busy)}>
              <Check size={17} aria-hidden="true" />
              {busy === 'complete' ? t('loadingShort') : t('completeActivity')}
            </button>
          )}
          {assignment.status === 'completed' && !reassessment && (
            <button className="button button-secondary" onClick={openReassessment} disabled={Boolean(busy)}>
              {busy === 'reassessment' ? t('loadingShort') : t('startReassessment')}
            </button>
          )}
          {completed && <p className="status-message" role="status">{t('activityComplete')}</p>}

          {reassessment && (
            <article className="panel reassessment-panel">
              <p className="eyebrow">{t('reassessmentTitle')}</p>
              <h2>{t('reassessmentInstructions')}</h2>
              {reassessmentDone ? (
                <>
                  <div className="result-summary">
                    <strong>{reassessment.accuracy_percentage}%</strong>
                    <span>{reassessment.correct_answers} / {reassessment.total_questions} {t('correct').toLowerCase()}</span>
                  </div>
                  {reassessment.questions?.length > 0 && (
                    <div className="question-stack">
                      {reassessment.questions.map((question, index) => {
                        const result = reassessment.results?.find((item) => item.question_id === question.id);
                        return (
                          <div className="practice-question" key={question.id}>
                            <label htmlFor={`reassessment-${question.id}`}>
                              <span className="question-number">{index + 1}</span> {question.question}
                            </label>
                            <input
                              id={`reassessment-${question.id}`}
                              value={reassessmentAnswers[question.id] || result?.answer || ''}
                              disabled
                              readOnly
                            />
                            {result && (
                              <span className={result.is_correct ? 'answer-feedback correct' : 'answer-feedback incorrect'}>
                                {result.is_correct ? t('correct') : t('incorrect')}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              ) : (
                <form onSubmit={sendReassessment}>
                  <div className="question-stack">
                    {reassessment.questions.map((question, index) => (
                      <div className="practice-question" key={question.id}>
                        <label htmlFor={`reassessment-${question.id}`}>
                          <span className="question-number">{index + 1}</span> {question.question}
                        </label>
                        <input
                          id={`reassessment-${question.id}`}
                          value={reassessmentAnswers[question.id] || ''}
                          onChange={(event) => setReassessmentAnswers((answers) => ({
                            ...answers,
                            [question.id]: event.target.value,
                          }))}
                          placeholder={t('answerPlaceholder')}
                          required
                        />
                      </div>
                    ))}
                  </div>
                  <button className="button button-primary" disabled={Boolean(busy)}>
                    {busy === 'submit-reassessment' ? t('loadingShort') : t('submitReassessment')}
                  </button>
                </form>
              )}
            </article>
          )}
        </div>
        <aside className="activity-aside">
          <div className="panel">
            <p className="eyebrow">{t('learningObjective')}</p>
            <p>{intervention.learning_objective}</p>
            {assignment.status === 'completed' && (
              <span className="status-pill status-completed">{t('completed')}</span>
            )}
          </div>
          <Link className="text-link" to="/student/dashboard">{t('backToLearning')}</Link>
        </aside>
      </section>
    </div>
  );
}
