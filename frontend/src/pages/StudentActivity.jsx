import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, Check } from 'lucide-react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import {
  EmptyState,
  ErrorState,
  LoadingState,
  RefreshNotice,
} from '../components/PageStates';
import Tabs from '../components/ui/Tabs';
import QuestionPager from '../components/ui/QuestionPager';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { getErrorMessage } from '../services/api';
import {
  completeIntervention,
  getStudentAssignment,
  getStudentInterventions,
  getStudentReassessment,
  submitPractice,
  submitReassessment,
} from '../services/classpulseApi';

export function StudentActivityList({ studentId }) {
  const { t } = useI18n();
  const loadStudentAssignments = useCallback(
    () => getStudentInterventions(studentId),
    [studentId],
  );
  const {
    data: assignments,
    loading,
    error,
    refreshing,
    reload,
  } = useAsyncData(loadStudentAssignments, studentId);
  if (loading) return <LoadingState />;
  if (error && !assignments)
    return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="page-content">
      <RefreshNotice error={error} refreshing={refreshing} onRetry={reload} />
      <PageHeader
        eyebrow={t('interventions')}
        title={t('assignedActivities')}
      />
      {assignments.length ? (
        <div className="student-activity-grid">
          {assignments.map((item) => (
            <article className="student-activity-card" key={item.id}>
              <div className="diagnosis-meta">
                <span className="code-pill">
                  {item.intervention.misconception_code}
                </span>
                <span className={`status-pill status-${item.status}`}>
                  {t(item.status)}
                </span>
              </div>
              <h2>{item.intervention.title}</h2>
              <p>{item.intervention.learning_objective}</p>
              <Link
                className="button button-primary"
                to={`/student/interventions/${item.id}`}
              >
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

export function StudentActivity({ assignmentId, studentId }) {
  const { t } = useI18n();
  const loadAssignment = useCallback(
    () => getStudentAssignment(assignmentId, studentId),
    [assignmentId, studentId],
  );
  const { data, loading, error, refreshing, reload } = useAsyncData(
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
  const [activityStep, setActivityStep] = useState('learn');
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
          console.error(
            '[ClassPulse] Failed to auto-restore reassessment',
            loadErr,
          );
        });
    }
  }, [data, studentId]);

  if (loading) return <LoadingState />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;

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
      <RefreshNotice error={error} refreshing={refreshing} onRetry={reload} />
      <PageHeader
        eyebrow={`${intervention.misconception_code} · ${t('targetedPractice')}`}
        title={intervention.title}
        description={intervention.introduction}
      />
      {actionError && (
        <p className="form-error" role="alert">
          {actionError}
        </p>
      )}

      <Tabs
        label={t('targetedPractice')}
        value={activityStep}
        onChange={setActivityStep}
        items={[
          { value: 'learn', label: t('learnAndExample') },
          { value: 'practice', label: t('practiceStep') },
          { value: 'finish', label: t('finishStep') },
        ]}
      >
        <section className="activity-layout">
          <div className="activity-main">
            <article
              className="panel learning-panel"
              hidden={activityStep !== 'learn'}
            >
              <p className="eyebrow">{t('learningObjective')}</p>
              <h2>{intervention.learning_objective}</h2>
              <p className="learning-explanation">{intervention.explanation}</p>
              <div className="example-box">
                <p className="eyebrow">{t('guidedExample')}</p>
                <strong>{intervention.guided_example.question}</strong>
                <p>{intervention.guided_example.steps}</p>
                <p className="example-answer">
                  <strong>{t('expectedAnswer')}:</strong>{' '}
                  {intervention.guided_example.answer}
                </p>
              </div>
            </article>

            <article className="panel" hidden={activityStep !== 'practice'}>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">{t('practice')}</p>
                  <h2>{t('activityInstructions')}</h2>
                </div>
              </div>
              <p className="body-copy">{intervention.instructions}</p>
              <form onSubmit={checkPractice}>
                <QuestionPager
                  questions={intervention.practice_questions}
                  busy={Boolean(busy)}
                  submitLabel={
                    !practiceChecked && assignment.status !== 'completed'
                      ? t('submitPractice')
                      : null
                  }
                >
                  {(question, index) => {
                    const result = practiceResult?.results.find(
                      (item) => item.question_index === question.question_index,
                    );
                    return (
                      <div className="practice-question">
                        <h3 tabIndex={-1} data-question-heading>
                          <span className="question-number">{index + 1}</span>{' '}
                          {question.question}
                        </h3>
                        <label htmlFor={`practice-${question.question_index}`}>
                          {t('answer')}
                        </label>
                        <input
                          id={`practice-${question.question_index}`}
                          value={practiceAnswers[question.question_index] || ''}
                          onChange={(event) =>
                            setPracticeAnswers((answers) => ({
                              ...answers,
                              [question.question_index]: event.target.value,
                            }))
                          }
                          placeholder={t('answerPlaceholder')}
                          disabled={
                            practiceChecked ||
                            assignment.status === 'completed' ||
                            Boolean(busy)
                          }
                          required
                        />
                        <span className="field-help">{question.hint}</span>
                        {result && (
                          <span
                            className={
                              result.is_correct
                                ? 'answer-feedback correct'
                                : 'answer-feedback incorrect'
                            }
                          >
                            {result.is_correct ? t('correct') : t('incorrect')}
                          </span>
                        )}
                      </div>
                    );
                  }}
                </QuestionPager>
              </form>
            </article>

            <div className="activity-finish" hidden={activityStep !== 'finish'}>
              {!practiceChecked && assignment.status !== 'completed' && (
                <p className="notice-inline">{t('finishPracticeFirst')}</p>
              )}
              {practiceResult && (
                <p className="status-message" role="status">
                  {t('practiceScore', {
                    correct: practiceResult.correct_answers,
                    total:
                      practiceResult.correct_answers +
                      practiceResult.incorrect_answers,
                  })}
                </p>
              )}

              {!reassessment &&
                assignment.status !== 'completed' &&
                practiceChecked && (
                  <button
                    className="button button-primary"
                    onClick={finishActivity}
                    disabled={Boolean(busy)}
                  >
                    <Check size={17} aria-hidden="true" />
                    {busy === 'complete'
                      ? t('loadingShort')
                      : t('completeActivity')}
                  </button>
                )}
              {assignment.status === 'completed' && !reassessment && (
                <button
                  className="button button-secondary"
                  onClick={openReassessment}
                  disabled={Boolean(busy)}
                >
                  {busy === 'reassessment'
                    ? t('loadingShort')
                    : t('startReassessment')}
                </button>
              )}
              {completed && (
                <p className="status-message" role="status">
                  {t('activityComplete')}
                </p>
              )}

              {reassessment && (
                <article className="panel reassessment-panel">
                  <p className="eyebrow">{t('reassessmentTitle')}</p>
                  <h2>{t('reassessmentInstructions')}</h2>
                  {reassessmentDone ? (
                    <>
                      <div className="result-summary">
                        <strong>{reassessment.accuracy_percentage}%</strong>
                        <span>
                          {reassessment.correct_answers} /{' '}
                          {reassessment.total_questions}{' '}
                          {t('correct').toLowerCase()}
                        </span>
                      </div>
                      {reassessment.questions?.length > 0 && (
                        <div className="question-stack">
                          {reassessment.questions.map((question, index) => {
                            const result = reassessment.results?.find(
                              (item) => item.question_id === question.id,
                            );
                            return (
                              <div
                                className="practice-question"
                                key={question.id}
                              >
                                <label htmlFor={`reassessment-${question.id}`}>
                                  <span className="question-number">
                                    {index + 1}
                                  </span>{' '}
                                  {question.question}
                                </label>
                                <input
                                  id={`reassessment-${question.id}`}
                                  value={
                                    reassessmentAnswers[question.id] ||
                                    result?.answer ||
                                    ''
                                  }
                                  disabled
                                  readOnly
                                />
                                {result && (
                                  <span
                                    className={
                                      result.is_correct
                                        ? 'answer-feedback correct'
                                        : 'answer-feedback incorrect'
                                    }
                                  >
                                    {result.is_correct
                                      ? t('correct')
                                      : t('incorrect')}
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
                      <QuestionPager
                        questions={reassessment.questions}
                        busy={Boolean(busy)}
                        submitLabel={t('submitReassessment')}
                      >
                        {(question, index) => (
                          <div className="practice-question">
                            <h3 tabIndex={-1} data-question-heading>
                              <span className="question-number">
                                {index + 1}
                              </span>{' '}
                              {question.question}
                            </h3>
                            <label htmlFor={`reassessment-${question.id}`}>
                              {t('answer')}
                            </label>
                            <input
                              id={`reassessment-${question.id}`}
                              value={reassessmentAnswers[question.id] || ''}
                              onChange={(event) =>
                                setReassessmentAnswers((answers) => ({
                                  ...answers,
                                  [question.id]: event.target.value,
                                }))
                              }
                              placeholder={t('answerPlaceholder')}
                              disabled={Boolean(busy)}
                              required
                            />
                          </div>
                        )}
                      </QuestionPager>
                    </form>
                  )}
                </article>
              )}
            </div>
          </div>
          <aside className="activity-aside">
            <div className="panel">
              <p className="eyebrow">{t('learningObjective')}</p>
              <p>{intervention.learning_objective}</p>
              {assignment.status === 'completed' && (
                <span className="status-pill status-completed">
                  {t('completed')}
                </span>
              )}
            </div>
            <Link className="text-link" to="/student/dashboard">
              {t('backToLearning')}
            </Link>
          </aside>
        </section>
      </Tabs>
    </div>
  );
}
