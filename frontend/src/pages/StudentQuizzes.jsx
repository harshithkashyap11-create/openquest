import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  BookOpenCheck,
  Check,
  MessageCircle,
  Send,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { getErrorMessage } from '../services/api';
import {
  answerRepair,
  reflectOnQuestion,
  studentQuiz,
  studentQuizzes,
  submitQuiz,
} from '../services/quizApi';
import './Quizzes.css';

const letters = 'ABCD';

export default function StudentQuizzes() {
  const { quizId } = useParams();
  const { session } = useDemoSession();
  const { t } = useI18n();
  const load = useCallback(
    () => studentQuizzes(session.studentId),
    [session.studentId],
  );
  const { data, loading, error, reload } = useAsyncData(
    load,
    session.studentId,
  );
  if (quizId)
    return (
      <StudentQuiz
        key={`${session.studentId}:${quizId}`}
        quizId={quizId}
        studentId={session.studentId}
      />
    );
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return (
    <div className="page-content quiz-page">
      <PageHeader
        eyebrow={t('studentView')}
        title={t('quizzes')}
        description={t('quizStudentIntro')}
        actions={
          <button className="button button-secondary" onClick={reload}>
            {t('refreshQuizzes')}
          </button>
        }
      />
      {data.length ? (
        <div className="quiz-list">
          {data.map((quiz) => (
            <Link
              className="quiz-list-row"
              key={quiz.id}
              to={`/student/quizzes/${quiz.id}`}
              aria-label={quiz.title}
            >
              <BookOpenCheck size={22} aria-hidden="true" />
              <span>
                <strong>{quiz.title}</strong>
                <small>
                  {quiz.question_count} {t('questions')} ·{' '}
                  {quiz.submitted ? t('quizReview') : t('quizReady')}
                </small>
              </span>
              <ArrowRight size={18} aria-hidden="true" />
            </Link>
          ))}
        </div>
      ) : (
        <section className="panel">
          <EmptyState title={t('noPublishedQuizzes')}>
            {t('quizWaitTeacher')}
          </EmptyState>
        </section>
      )}
    </div>
  );
}

function StudentQuiz({ quizId, studentId }) {
  const { t } = useI18n();
  const load = useCallback(
    () => studentQuiz(studentId, quizId),
    [studentId, quizId],
  );
  const { data, loading, error, reload } = useAsyncData(
    load,
    `${studentId}:${quizId}`,
  );
  const [answers, setAnswers] = useState({});
  const [attempt, setAttempt] = useState(null);
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const result = attempt || data.attempt;
  const focusQuestion = data.questions.find((q) => q.id === selectedQuestion);
  const focusResult = result?.results.find(
    (r) => r.question_id === selectedQuestion,
  );
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setActionError('');
    try {
      setAttempt(
        await submitQuiz(
          studentId,
          quizId,
          data.questions.map((q) => ({
            question_id: q.id,
            selected_option: answers[q.id],
          })),
        ),
      );
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  function saveReflection(reflection) {
    setAttempt((current) => {
      const previous = current || data.attempt;
      return {
        ...previous,
        results: previous.results.map((r) =>
          r.question_id === selectedQuestion ? { ...r, reflection } : r,
        ),
      };
    });
  }
  return (
    <div className="page-content quiz-page">
      <Link className="text-link quiz-back" to="/student/quizzes">
        <ArrowLeft size={16} aria-hidden="true" />
        {t('allQuizzes')}
      </Link>
      <PageHeader
        eyebrow={t('quizzes')}
        title={data.title}
        description={result ? t('quizReflectIntro') : t('quizSubmitIntro')}
      />
      {actionError && (
        <p className="form-error" role="alert">
          {actionError}
        </p>
      )}
      {result ? (
        <>
          <section
            className="quiz-result-strip"
            aria-labelledby="quiz-result-title"
          >
            <div>
              <h2 id="quiz-result-title">{t('yourResult')}</h2>
              <p>{t('quizScoreNote')}</p>
            </div>
            <strong>
              {result.score} / {result.total}
              <small>{t('marks')}</small>
            </strong>
          </section>
          <div
            className={`quiz-learning-layout ${focusQuestion ? 'has-sidebar' : ''}`}
          >
            <div className="quiz-result-list">
              {data.questions.map((q, index) => {
                const item = result.results.find((r) => r.question_id === q.id);
                return (
                  <article
                    className={`panel quiz-result-question ${selectedQuestion === q.id ? 'selected' : ''}`}
                    key={q.id}
                  >
                    <div className="panel-heading">
                      <p className="eyebrow">
                        {t('questionNumber', { number: index + 1 })}
                      </p>
                      <span
                        className={`quiz-label ${item.is_correct ? 'published' : 'missed'}`}
                      >
                        {item.is_correct
                          ? t('quizCorrect')
                          : t('quizNeedsReview')}{' '}
                        · {item.is_correct ? '1' : '0'} / 1
                      </span>
                    </div>
                    <h2>{q.text}</h2>
                    <p>
                      {t('yourAnswer')}:{' '}
                      <strong>
                        {letters[item.selected_option]}.{' '}
                        {q.options[item.selected_option]}
                      </strong>
                    </p>
                    {item.is_correct ? (
                      <p className="muted-note">{item.explanation}</p>
                    ) : (
                      <button
                        className="button button-secondary"
                        aria-label={t('reflectOnQuestion', {
                          number: index + 1,
                        })}
                        onClick={() => setSelectedQuestion(q.id)}
                      >
                        <MessageCircle size={16} aria-hidden="true" />
                        {item.reflection
                          ? t('continueReflection')
                          : t('understandMistake')}
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
            {focusQuestion && (
              <ReflectionSidebar
                key={focusQuestion.id}
                question={focusQuestion}
                result={focusResult}
                studentId={studentId}
                quizId={quizId}
                onChange={saveReflection}
              />
            )}
          </div>
        </>
      ) : (
        <form className="quiz-take" onSubmit={submit}>
          {data.questions.map((q, index) => (
            <fieldset className="panel quiz-question" key={q.id}>
              <legend>
                <span className="eyebrow">
                  {t('questionNumber', { number: index + 1 })}
                </span>
                <span>{q.text}</span>
              </legend>
              <div className="quiz-options">
                {q.options.map((option, i) => (
                  <label className="quiz-option" key={i}>
                    <input
                      type="radio"
                      name={q.id}
                      required
                      checked={answers[q.id] === i}
                      onChange={() =>
                        setAnswers((old) => ({ ...old, [q.id]: i }))
                      }
                    />
                    <span>
                      {letters[i]}. {option}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          <div className="quiz-savebar">
            <span>
              {t('quizAnsweredCount', {
                count: Object.keys(answers).length,
                total: data.questions.length,
              })}
            </span>
            <button
              className="button button-primary"
              disabled={
                busy || Object.keys(answers).length !== data.questions.length
              }
            >
              <Send size={16} aria-hidden="true" />
              {busy ? t('loadingShort') : t('submitQuiz')}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function ReflectionSidebar({ question, result, studentId, quizId, onChange }) {
  const { t, language } = useI18n();
  const headingRef = useRef(null);
  useEffect(() => {
    headingRef.current?.focus();
  }, []);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [repairAnswer, setRepairAnswer] = useState(null);
  const reflection = result.reflection;
  const repair = reflection?.repair;
  async function send(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      onChange(
        await reflectOnQuestion(
          studentId,
          quizId,
          question.id,
          message,
          language,
        ),
      );
      setMessage('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  async function checkRepair(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const next = await answerRepair(
        studentId,
        quizId,
        question.id,
        repairAnswer,
      );
      onChange({ ...reflection, repair: { ...repair, result: next } });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="quiz-reflection" aria-labelledby="reflection-heading">
      <header className="quiz-reflection-header">
        <span className="quiz-reflection-icon">
          <MessageCircle size={21} aria-hidden="true" />
        </span>
        <div>
          <p className="eyebrow">{t('learningCompanion')}</p>
          <h2 ref={headingRef} tabIndex={-1} id="reflection-heading">
            {t('letsUnderstand')}
          </h2>
        </div>
      </header>
      <p>{t('whyThisOption', { option: letters[result.selected_option] })}</p>
      <blockquote className="quiz-chosen-answer">
        {question.options[result.selected_option]}
      </blockquote>
      {!reflection && <p className="muted-note">{t('reasoningPrompt')}</p>}
      {reflection && (
        <>
          <div className="quiz-feedback-meta">
            <span className="quiz-label">
              {reflection.feedback.provider === 'template'
                ? t('templateFeedback')
                : t('aiFeedback')}
            </span>
            <span className="quiz-label">
              {t(`quizError_${reflection.feedback.error_type}`)}
            </span>
          </div>
          <p className="muted-note">{t('tentativeNote')}</p>
          <div
            className="quiz-conversation"
            aria-live="polite"
            aria-relevant="additions"
          >
            {reflection.messages.map((item, index) => (
              <div className={`quiz-message ${item.role}`} key={index}>
                <small>
                  {item.role === 'student' ? t('you') : t('learningCompanion')}
                </small>
                <p>{item.content}</p>
              </div>
            ))}
          </div>
        </>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {!reflection || reflection.messages.length < 10 ? (
        <form className="quiz-reflection-form" onSubmit={send}>
          <div className="quiz-field">
            <label htmlFor="reflection-message">{t('explainThinking')}</label>
            <textarea
              id="reflection-message"
              required
              maxLength={2000}
              rows={4}
              value={message}
              disabled={busy}
              onChange={(e) => setMessage(e.target.value)}
            />
          </div>
          <button
            className="button button-primary"
            disabled={busy || !message.trim()}
          >
            <Send size={16} aria-hidden="true" />
            {busy ? t('loadingShort') : t('sendExplanation')}
          </button>
        </form>
      ) : (
        <p>{t('reflectionLimit')}</p>
      )}
      {repair && (
        <section className="quiz-repair" aria-labelledby="repair-heading">
          <h3 id="repair-heading">{t('repairChallenge')}</h3>
          <p>{repair.text}</p>
          {repair.result ? (
            <div role="status">
              <strong>
                {repair.result.is_correct
                  ? t('repairCorrect')
                  : t('repairTryTeacher')}
              </strong>
              <p>{repair.result.explanation}</p>
              <p className="muted-note">{t('repairObservation')}</p>
            </div>
          ) : (
            <form onSubmit={checkRepair}>
              <details>
                <summary>{t('showHint')}</summary>
                <p>{repair.hint}</p>
              </details>
              <fieldset className="quiz-options quiz-repair-options">
                <legend className="sr-only">{t('repairChallenge')}</legend>
                {repair.options.map((option, index) => (
                  <label className="quiz-option" key={index}>
                    <input
                      type="radio"
                      name="repair-answer"
                      checked={repairAnswer === index}
                      onChange={() => setRepairAnswer(index)}
                      required
                    />
                    <span>
                      {letters[index]}. {option}
                    </span>
                  </label>
                ))}
              </fieldset>
              <button
                className="button button-secondary"
                disabled={busy || repairAnswer === null}
              >
                <Check size={16} aria-hidden="true" />
                {t('checkRepair')}
              </button>
            </form>
          )}
        </section>
      )}
    </aside>
  );
}
