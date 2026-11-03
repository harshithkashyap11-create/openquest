import { useI18n } from '../i18n/useI18n';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  Check,
  FileUp,
  Plus,
  Radio,
  Save,
  Send,
  Trash2,
} from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import useAsyncData from '../hooks/useAsyncData';
import { getErrorMessage } from '../services/api';
import {
  importQuiz,
  listQuizzes,
  publishQuiz,
  quizInsights,
  reviewLesson,
  reviewReflection,
  saveQuiz,
  suggestLesson,
} from '../services/quizApi';
import './Quizzes.css';

const letters = 'ABCD';
const blankQuestion = () => ({
  text: '',
  options: ['', '', '', ''],
  correct_option: 0,
  explanation: '',
  concept: '',
  repair: null,
});
const blankRepair = () => ({
  text: '',
  options: ['', '', '', ''],
  correct_option: 0,
  explanation: '',
  hint: '',
});

export default function TeacherQuizzes() {
  const { t } = useI18n();
  const { session } = useDemoSession();
  const load = useCallback(
    () => listQuizzes(session.classId),
    [session.classId],
  );
  const { data, loading, error, reload } = useAsyncData(load, session.classId);
  const [selected, setSelected] = useState(null);
  const [creating, setCreating] = useState(false);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (creating || selected)
    return (
      <QuizWorkspace
        key={`${session.classId}:${selected?.id || 'new'}`}
        quiz={selected}
        classId={session.classId}
        onBack={() => {
          setSelected(null);
          setCreating(false);
          reload();
        }}
      />
    );
  return (
    <div className="page-content quiz-page">
      <PageHeader
        eyebrow={t('CLASSROOM CHECKPOINTS')}
        title={t('Quizzes')}
        description={t('Ask. Understand. Help the next lesson land.')}
        actions={
          <button
            className="button button-primary"
            onClick={() => setCreating(true)}
          >
            <Plus size={17} aria-hidden="true" />
            {t('Create quiz')}
          </button>
        }
      />
      <section className="quiz-intro">
        <span className="quiz-step">
          01 <strong>{t('Publish a checkpoint')}</strong>
        </span>
        <span className="quiz-step">
          02 <strong>{t('Listen to the reasoning')}</strong>
        </span>
        <span className="quiz-step">
          03 <strong>{t('Teach what matters next')}</strong>
        </span>
      </section>
      {data.length ? (
        <div className="quiz-list">
          {data.map((quiz) => (
            <button
              className="quiz-list-row"
              key={quiz.id}
              onClick={() => setSelected(quiz)}
            >
              <span className={`quiz-label ${quiz.status}`}>{quiz.status}</span>
              <span>
                <strong>{quiz.title}</strong>
                <small>
                  {quiz.questions.length} {t('questions · 1 mark each')}
                </small>
              </span>
              <span className="quiz-row-action">
                {quiz.status === 'draft'
                  ? t('Review draft →')
                  : t('Live insights →')}
              </span>
            </button>
          ))}
        </div>
      ) : (
        <section className="panel">
          <EmptyState title={t('Your first quiz starts here')}>
            {t(
              'Create questions or import a CSV, review the answer keys, then publish to this class.',
            )}
          </EmptyState>
        </section>
      )}
    </div>
  );
}

function QuizWorkspace({ quiz, classId, onBack }) {
  const { t } = useI18n();
  const [saved, setSaved] = useState(quiz);
  const [title, setTitle] = useState(quiz?.title || '');
  const [questions, setQuestions] = useState(
    quiz?.questions || [blankQuestion()],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [dirty, setDirty] = useState(!quiz);
  const importRef = useRef(null);
  const published = saved?.status === 'published';

  const updateQuestion = (index, value) => {
    setQuestions((current) => current.map((q, i) => (i === index ? value : q)));
    setDirty(true);
  };
  async function importContent(content) {
    const result = await importQuiz(classId, content);
    if (result.errors.length) throw new Error(result.errors.join('\n'));
    setQuestions(result.questions);
    setDirty(true);
    setNotice(t('quizImportedNotice', { count: result.questions.length }));
  }
  async function importFile(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setError('');
    setBusy(true);
    try {
      if (!file.name.toLowerCase().endsWith('.csv') || file.size > 200000)
        throw new Error(t('quizCsvLimit'));
      await importContent(await file.text());
    } catch (err) {
      setError(err.response ? getErrorMessage(err) : err.message);
    } finally {
      setBusy(false);
    }
  }
  async function loadExample() {
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/fractions-quiz-example.csv');
      if (!response.ok) throw new Error(t('quizExampleFailed'));
      await importContent(await response.text());
      if (!title) setTitle('Fractions checkpoint');
    } catch (err) {
      setError(err.response ? getErrorMessage(err) : err.message);
    } finally {
      setBusy(false);
    }
  }
  async function persist(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const payload = {
        title,
        questions: questions.map(({ id: _id, ...q }) => q),
      };
      const result = await saveQuiz(classId, saved?.id, payload);
      setSaved(result);
      setQuestions(result.questions);
      setDirty(false);
      setNotice(t('quizDraftSavedNotice'));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  async function publish() {
    setBusy(true);
    setError('');
    try {
      setSaved(await publishQuiz(classId, saved.id));
      setNotice('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page-content quiz-page">
      <button className="text-link quiz-back" onClick={onBack}>
        <ArrowLeft size={16} aria-hidden="true" />
        {t('All quizzes')}
      </button>
      <PageHeader
        eyebrow={published ? t('LIVE CLASSROOM') : t('QUIZ STUDIO')}
        title={
          published
            ? saved.title
            : saved
              ? t('Review your quiz')
              : t('Create a quiz')
        }
        description={
          published
            ? t('Responses and student reasoning, as they arrive.')
            : t('One focused topic. Clear questions. Teacher-approved answers.')
        }
      />
      {error && (
        <p className="form-error quiz-prewrap" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="status-message" role="status">
          {notice}
        </p>
      )}
      {published ? (
        <>
          <span className="quiz-label published">{t('Published quiz')}</span>
          <LiveInsights quiz={saved} classId={classId} />
        </>
      ) : (
        <form className="quiz-editor" onSubmit={persist}>
          <div className="quiz-toolbar">
            <button
              type="button"
              className="button button-secondary"
              onClick={() => importRef.current.click()}
              disabled={busy}
            >
              <FileUp size={16} aria-hidden="true" />
              {t('Import CSV')}
            </button>
            <a className="text-link" href="/quiz-template.csv" download>
              {t('Download CSV template')}
            </a>
            <button
              type="button"
              className="text-link"
              onClick={loadExample}
              disabled={busy}
            >
              {t('Load fractions example')}
            </button>
            <input
              ref={importRef}
              type="file"
              accept=".csv,text/csv"
              onChange={importFile}
              className="sr-only"
              aria-label={t('Upload quiz CSV')}
            />
          </div>
          <label className="quiz-field" htmlFor="quiz-title">
            {t('Quiz title')}
            <input
              id="quiz-title"
              required
              maxLength={160}
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setDirty(true);
              }}
            />
          </label>
          {questions.map((question, index) => (
            <section className="panel quiz-editor-question" key={index}>
              <div className="panel-heading">
                <h2>
                  {t('Question')} {index + 1}
                </h2>
                <button
                  type="button"
                  className="button button-secondary"
                  aria-label={`Remove question ${index + 1}`}
                  disabled={busy || questions.length === 1}
                  onClick={() => {
                    setQuestions((current) =>
                      current.filter((_, i) => i !== index),
                    );
                    setDirty(true);
                  }}
                >
                  <Trash2 size={15} aria-hidden="true" />
                  {t('Remove')}
                </button>
              </div>
              <QuestionFields
                question={question}
                prefix={`q${index}`}
                update={(value) => updateQuestion(index, value)}
              />
              <label className="quiz-field" htmlFor={`concept-${index}`}>
                {t('Concept or skill')}
                <input
                  id={`concept-${index}`}
                  maxLength={200}
                  value={question.concept}
                  onChange={(e) =>
                    updateQuestion(index, {
                      ...question,
                      concept: e.target.value,
                    })
                  }
                />
              </label>
              <label className="quiz-check">
                <input
                  type="checkbox"
                  checked={!!question.repair}
                  onChange={(e) =>
                    updateQuestion(index, {
                      ...question,
                      repair: e.target.checked ? blankRepair() : null,
                    })
                  }
                />
                {t('Add a repair challenge after reflection')}
              </label>
              {question.repair && (
                <details className="quiz-repair-editor" open>
                  <summary>{t('Teacher-approved follow-up question')}</summary>
                  <QuestionFields
                    question={question.repair}
                    prefix={`repair-${index}`}
                    repair
                    update={(value) =>
                      updateQuestion(index, { ...question, repair: value })
                    }
                  />
                </details>
              )}
            </section>
          ))}
          <div className="quiz-toolbar">
            <button
              type="button"
              className="button button-secondary"
              disabled={questions.length >= 20 || busy}
              onClick={() => {
                setQuestions((current) => [...current, blankQuestion()]);
                setDirty(true);
              }}
            >
              <Plus size={16} aria-hidden="true" />
              {t('Add question')}
            </button>
            <span className="muted-note">
              {questions.length} {t('/ 20 questions · 1 mark each')}
            </span>
          </div>
          <div className="quiz-savebar">
            <span>
              {t('Published questions stay fixed for consistent grading.')}
            </span>
            <button className="button button-secondary" disabled={busy}>
              <Save size={16} aria-hidden="true" />
              {busy ? t('Saving…') : t('Save draft')}
            </button>
            {saved && (
              <button
                type="button"
                className="button button-primary"
                onClick={publish}
                disabled={busy || dirty}
              >
                <Send size={16} aria-hidden="true" />
                {t('Publish quiz')}
              </button>
            )}
          </div>
          {saved && dirty && (
            <p className="muted-note">
              {t('Save your changes before publishing.')}
            </p>
          )}
        </form>
      )}
    </div>
  );
}

function QuestionFields({ question, prefix, update, repair = false }) {
  const { t } = useI18n();
  return (
    <>
      <div className="quiz-field">
        <label htmlFor={`${prefix}-text`}>
          {repair ? t('Repair question') : t('Question')}
        </label>
        <textarea
          id={`${prefix}-text`}
          required
          maxLength={2000}
          value={question.text}
          onChange={(e) => update({ ...question, text: e.target.value })}
        />
      </div>
      <div className="quiz-options-editor">
        {question.options.map((option, index) => (
          <label
            className="quiz-field"
            htmlFor={`${prefix}-${index}`}
            key={index}
          >
            {t('Option')} {letters[index]}
            <input
              id={`${prefix}-${index}`}
              required
              maxLength={500}
              value={option}
              onChange={(e) =>
                update({
                  ...question,
                  options: question.options.map((old, i) =>
                    i === index ? e.target.value : old,
                  ),
                })
              }
            />
          </label>
        ))}
      </div>
      <label className="quiz-field" htmlFor={`${prefix}-key`}>
        {t('Correct option')}
        <select
          id={`${prefix}-key`}
          value={question.correct_option}
          onChange={(e) =>
            update({ ...question, correct_option: Number(e.target.value) })
          }
        >
          {question.options.map((_, i) => (
            <option value={i} key={i}>
              {letters[i]}
            </option>
          ))}
        </select>
      </label>
      <div className="quiz-field">
        <label htmlFor={`${prefix}-explanation`}>
          {t('Teacher explanation')}
        </label>
        <textarea
          id={`${prefix}-explanation`}
          required
          maxLength={2000}
          value={question.explanation}
          onChange={(e) => update({ ...question, explanation: e.target.value })}
        />
      </div>
      {repair && (
        <label className="quiz-field" htmlFor={`${prefix}-hint`}>
          {t('Hint')}
          <input
            id={`${prefix}-hint`}
            required
            maxLength={2000}
            value={question.hint}
            onChange={(e) => update({ ...question, hint: e.target.value })}
          />
        </label>
      )}
    </>
  );
}

function LiveInsights({ quiz, classId }) {
  const { t, language } = useI18n();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [lessonText, setLessonText] = useState('');
  const [lessonDirty, setLessonDirty] = useState(false);
  const load = useCallback(
    async (signal) => {
      const next = await quizInsights(classId, quiz.id, signal);
      setReport(next);
      setError('');
      return next;
    },
    [classId, quiz.id],
  );
  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function poll() {
      try {
        if (document.visibilityState === 'visible')
          await load(controller.signal);
      } catch (err) {
        if (err.code !== 'ERR_CANCELED') setError(getErrorMessage(err));
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, 5000);
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [load]);
  async function action(run) {
    setBusy(true);
    setError('');
    try {
      await run();
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  if (!report)
    return error ? (
      <ErrorState
        error={error}
        onRetry={() => void load().catch((e) => setError(getErrorMessage(e)))}
      />
    ) : (
      <LoadingState />
    );
  const lesson = report.lesson;
  return (
    <div className="quiz-report">
      <div className="quiz-live-line">
        <span>
          <Radio size={15} aria-hidden="true" />
          {t('Updates every 5 seconds')}
        </span>
        <span>
          {t('Last updated')}{' '}
          {new Intl.DateTimeFormat(language, {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          }).format(new Date(report.refreshed_at))}
        </span>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error} {t('Showing the last received data.')}
        </p>
      )}
      <div className="quiz-stats">
        <div>
          <small>{t('Submitted')}</small>
          <strong>
            {report.submitted_students} / {report.total_students}
          </strong>
        </div>
        <div>
          <small>{t('Shared reasoning')}</small>
          <strong>
            {report.questions.reduce((n, q) => n + q.reflected_students, 0)}
          </strong>
          <small>{t('question reflections')}</small>
        </div>
        <div>
          <small>{t('Repair answers correct')}</small>
          <strong>
            {report.questions.reduce((n, q) => n + q.repair_correct, 0)} /{' '}
            {report.questions.reduce((n, q) => n + q.repair_attempted, 0)}
          </strong>
          <small>{t('observed attempts')}</small>
        </div>
      </div>
      <p className="muted-note">
        {t(
          'Answer counts are observed. AI interpretations are tentative; uncertain and flagged cases are excluded from themes.',
        )}
      </p>
      {report.questions.map((q) => (
        <section className="panel quiz-insight" key={q.id}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                {t('QUESTION')} {q.ordinal} ·{' '}
                {q.concept || 'Understanding check'}
              </p>
              <h2>{q.text}</h2>
            </div>
            <span className="quiz-label">
              {q.correct_students} / {q.answered_students} {t('ui.correct')}
            </span>
          </div>
          <div className="quiz-distribution">
            {q.options.map((option, index) => (
              <div className="quiz-option-count" key={index}>
                <span>
                  {letters[index]}
                  {index === q.correct_option ? ' ✓' : ''}
                </span>
                <span>{option}</span>
                <meter
                  min="0"
                  max={Math.max(1, q.answered_students)}
                  value={q.option_counts[index]}
                  aria-label={t('optionResponseCount', {
                    option: letters[index],
                  })}
                />
                <strong>{q.option_counts[index]}</strong>
              </div>
            ))}
          </div>
          <p className="quiz-summary">
            {q.answered_students - q.correct_students} {t('of')}{' '}
            {q.answered_students} {t('students missed this question.')}{' '}
            {q.reflected_students} {t('shared reasoning;')}{' '}
            {q.uncertain_students} {t('uncertain;')} {q.flagged_students}{' '}
            {t('flagged.')}
          </p>
          <div className="quiz-themes">
            {q.themes.length ? (
              q.themes.map((theme) => (
                <span className="quiz-label" key={theme.error_type}>
                  {theme.error_type} · {theme.students} {t('ui.students')}
                </span>
              ))
            ) : (
              <span className="muted-note">
                {t('No supported error theme yet.')}
              </span>
            )}
          </div>
          <details className="quiz-evidence">
            <summary>{t('Student evidence')}</summary>
            {q.evidence.length ? (
              q.evidence.map((evidence) => (
                <article className="quiz-evidence-row" key={evidence.id}>
                  <div>
                    <strong>{evidence.student_code}</strong>
                    <span className="quiz-label">
                      {evidence.flagged ? t('Flagged') : evidence.error_type} ·{' '}
                      {evidence.provider}
                    </span>
                  </div>
                  <blockquote>
                    {evidence.quote || 'No verifiable quote returned.'}
                  </blockquote>
                  <p>{evidence.reply}</p>
                  <button
                    className="button button-secondary"
                    disabled={busy}
                    onClick={() =>
                      action(() =>
                        reviewReflection(
                          classId,
                          quiz.id,
                          evidence.id,
                          !evidence.flagged,
                        ),
                      )
                    }
                  >
                    {evidence.flagged
                      ? t('Restore interpretation')
                      : t('Flag interpretation')}
                  </button>
                </article>
              ))
            ) : (
              <p>{t('Students have not shared their reasoning yet.')}</p>
            )}
          </details>
        </section>
      ))}
      <section className="panel quiz-lesson">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('TURN INSIGHT INTO ACTION')}</p>
            <h2>{t('Your next five minutes')}</h2>
          </div>
          {!lesson && (
            <button
              className="button button-primary"
              disabled={busy || !report.submitted_students}
              onClick={() => action(() => suggestLesson(classId, quiz.id))}
            >
              {t('Suggest next lesson')}
            </button>
          )}
        </div>
        {lesson ? (
          <>
            <p className="muted-note">
              {lesson.generation_note} {lesson.provider} {t('· Based on')}{' '}
              {lesson.based_on_submissions} {t('submissions and')}{' '}
              {lesson.based_on_reflections} {t('reflections.')}{' '}
              {report.submitted_students > lesson.based_on_submissions
                ? t(
                    'More submissions have arrived since this suggestion was created.',
                  )
                : ''}
            </p>
            <div className="quiz-field">
              <label htmlFor="lesson-text">{t('Lesson suggestion')}</label>
              <textarea
                id="lesson-text"
                rows={11}
                maxLength={6000}
                value={lessonDirty ? lessonText : lesson.text}
                onChange={(e) => {
                  setLessonText(e.target.value);
                  setLessonDirty(true);
                }}
              />
            </div>
            <div className="quiz-toolbar">
              <button
                className="button button-primary"
                disabled={
                  busy || !(lessonDirty ? lessonText : lesson.text).trim()
                }
                onClick={() =>
                  action(async () => {
                    await reviewLesson(classId, quiz.id, {
                      text: lessonDirty ? lessonText : lesson.text,
                      status: 'accepted',
                    });
                    setLessonDirty(false);
                  })
                }
              >
                <Check size={16} aria-hidden="true" />
                {t('Accept lesson')}
              </button>
              <button
                className="button button-secondary"
                disabled={
                  busy || !(lessonDirty ? lessonText : lesson.text).trim()
                }
                onClick={() =>
                  action(async () => {
                    await reviewLesson(classId, quiz.id, {
                      text: lessonDirty ? lessonText : lesson.text,
                      status: 'rejected',
                    });
                    setLessonDirty(false);
                  })
                }
              >
                {t('Reject lesson')}
              </button>
              <span role="status">
                {lesson.status === 'accepted'
                  ? t('Lesson accepted')
                  : lesson.status === 'rejected'
                    ? t('Lesson rejected')
                    : t('Draft · teacher review required')}
              </span>
            </div>
          </>
        ) : (
          <p>
            {t(
              'A reviewable teaching suggestion will use this quiz’s actual results and teacher explanations.',
            )}
          </p>
        )}
      </section>
    </div>
  );
}
