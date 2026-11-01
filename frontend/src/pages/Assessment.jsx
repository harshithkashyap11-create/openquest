import { useCallback, useState } from 'react';
import { CheckCircle2, ClipboardList } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { getErrorMessage } from '../services/api';
import { getClassAssessment, submitAssessment } from '../services/classpulseApi';

export default function Assessment() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const loadAssessment = useCallback(
    () => getClassAssessment(session.classId, session.studentId),
    [session.classId, session.studentId],
  );
  const { data, loading, error, reload } = useAsyncData(
    loadAssessment,
    `${session.classId}:${session.studentId}`,
  );
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submissionInfo, setSubmissionInfo] = useState('');

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError('');
    try {
      const result = await submitAssessment(
        session.studentId,
        data.questions.map((question) => ({
          question_id: question.id,
          answer: answers[question.id]?.answer || '',
          explanation: answers[question.id]?.explanation || '',
        })),
      );
      setSubmitted(true);
      setAnswers({});
      setSubmissionInfo(`${result.submitted_count} ${t('answersSubmitted').toLowerCase()}`);
    } catch (requestError) {
      setSubmitError(getErrorMessage(requestError, t('assessmentSubmitError')));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-content">
      <PageHeader
        eyebrow={<><ClipboardList size={15} aria-hidden="true" /> {data.topic}</>}
        title={data.title || t('assessmentTitle')}
        description={t('assessmentInstructions')}
      />
      {!data.questions.length ? (
        <section className="panel">
          <EmptyState title={t('noAssessmentQuestions')} />
        </section>
      ) : submitted ? (
        <section className="panel confirmation-panel">
          <CheckCircle2 size={30} aria-hidden="true" />
          <h2>{t('assessmentSubmitted')}</h2>
          <p>{submissionInfo}</p>
          <button className="button button-secondary" onClick={() => setSubmitted(false)}>
            {t('submitAnotherAttempt')}
          </button>
        </section>
      ) : (
        <form className="assessment-form panel" onSubmit={handleSubmit}>
          <div className="assessment-progress">
            <span>{data.questions.length} {t('questions')}</span>
            <span>{t('explanationOptional')}</span>
          </div>
          <div className="question-stack">
            {data.questions.map((question, index) => (
              <article className="assessment-question" key={question.id}>
                <p className="question-count">{t('question')} {index + 1} <span>· {question.topic}</span></p>
                <h2>{question.question_text}</h2>
                <label htmlFor={`answer-${question.id}`}>{t('answer')}</label>
                <input
                  id={`answer-${question.id}`}
                  value={answers[question.id]?.answer || ''}
                  onChange={(event) => setAnswers((current) => ({
                    ...current,
                    [question.id]: { ...current[question.id], answer: event.target.value },
                  }))}
                  placeholder={t('answerPlaceholder')}
                  required
                />
                <label htmlFor={`explanation-${question.id}`}>{t('explanationOptional')}</label>
                <textarea
                  id={`explanation-${question.id}`}
                  rows={3}
                  value={answers[question.id]?.explanation || ''}
                  onChange={(event) => setAnswers((current) => ({
                    ...current,
                    [question.id]: { ...current[question.id], explanation: event.target.value },
                  }))}
                  placeholder={t('explanationPlaceholder')}
                />
              </article>
            ))}
          </div>
          {submitError && <p className="form-error" role="alert">{submitError}</p>}
          <button type="submit" className="button button-primary" disabled={submitting}>
            {submitting ? t('loadingShort') : t('submitAssessment')}
          </button>
        </form>
      )}
    </div>
  );
}
