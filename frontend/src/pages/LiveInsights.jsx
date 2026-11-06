import { useCallback, useEffect, useState } from 'react';
import { Check, Radio } from 'lucide-react';
import { ErrorState, LoadingState } from '../components/PageStates';
import { useI18n } from '../i18n/useI18n';
import { getErrorMessage } from '../services/api';
import {
  quizInsights,
  reviewLesson,
  reviewReflection,
  suggestLesson,
} from '../services/quizApi';

const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

export default function LiveInsights({ quiz, classId }) {
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
