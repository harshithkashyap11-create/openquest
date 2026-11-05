import { useI18n } from '../i18n/useI18n';
import { useCallback, useState } from 'react';
import { Plus } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import useAsyncData from '../hooks/useAsyncData';
import { listQuizzes } from '../services/quizApi';
import QuizWorkspace from './QuizWorkspace';
import './Quizzes.css';

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
