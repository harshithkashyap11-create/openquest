import { useRef, useState } from 'react';
import { ArrowLeft, FileUp, Plus, Save, Send, Trash2 } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { useI18n } from '../i18n/useI18n';
import { getErrorMessage } from '../services/api';
import { importQuiz, publishQuiz, saveQuiz } from '../services/quizApi';
import LiveInsights from './LiveInsights';

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

export default function QuizWorkspace({ quiz, classId, onBack }) {
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
