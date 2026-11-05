import Score from '../components/ui/ScoreCard';
import { ChartNoAxesCombined, ClipboardCheck, UsersRound } from 'lucide-react';
import { useCallback } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
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
import { getClassProgress } from '../services/classpulseApi';

export default function ClassProgress() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const loadProgress = useCallback(
    () => getClassProgress(session.classId),
    [session.classId],
  );
  const { data, loading, error, refreshing, reload } = useAsyncData(
    loadProgress,
    session.classId,
  );

  if (loading) return <LoadingState />;
  if (error && !data) return <ErrorState error={error} onRetry={reload} />;

  const initial = data.initial_assessment;
  const followup = data.followup_assessment;
  const hasScores = initial.sample_size > 0 || followup.sample_size > 0;
  const stages = [
    { stage: t('initialAccuracy'), accuracy: initial.sample_size > 0 ? initial.accuracy_percentage : null, sample: initial.sample_size },
    { stage: t('followupAccuracy'), accuracy: followup.sample_size > 0 ? followup.accuracy_percentage : null, sample: followup.sample_size },
  ];

  return (
    <div className="page-content">
      <RefreshNotice error={error} refreshing={refreshing} onRetry={reload} />
      <PageHeader
        eyebrow={t('classProgress')}
        title={t('classProgressTitle')}
        description={t('classProgressDescription')}
        actions={
          <button className="button button-secondary" onClick={reload}>
            {t('refresh')}
          </button>
        }
      />
      <section className="metric-grid metric-grid-three">
        <MetricCard
          label={t('activitiesAssigned')}
          value={data.assigned_interventions}
          icon={UsersRound}
        />
        <MetricCard
          label={t('activitiesCompleted')}
          value={data.completed_interventions}
          note={`${data.completed_interventions} / ${data.assigned_interventions}`}
          icon={ClipboardCheck}
        />
        <MetricCard
          label={t('reassessmentsCompleted')}
          value={data.completed_reassessments}
          icon={ChartNoAxesCombined}
        />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('scoreComparison')}</p>
            <h2>{t('classObservedScores')}</h2>
          </div>
          <span className="observed-badge">{t('observedScores')}</span>
        </div>
        {hasScores ? (
          <>
          <div className="progress-chart" aria-hidden="true">
            <ResponsiveContainer width="100%" height={270}>
              <LineChart data={stages} margin={{ top: 20, right: 30, left: 0, bottom: 12 }}>
                <CartesianGrid stroke="var(--cp-border)" vertical={false} />
                <XAxis dataKey="stage" tickLine={false} axisLine={false} padding={{ left: 28, right: 28 }} tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} unit="%" tickLine={false} axisLine={false} width={60} tick={{ fontSize: 12 }} />
                <Tooltip formatter={value => [`${value}%`, t('accuracy')]} />
                <Line type="linear" dataKey="accuracy" stroke="var(--cp-brand)" strokeWidth={3} dot={{ r: 5 }} activeDot={{ r: 7 }} connectNulls={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="field-help">{t('progressChartHelp')}</p>
          <div className="score-comparison progress-stage-data">
            <Score
              title={t('initialAccuracy')}
              correct={initial.correct_answers}
              sample={initial.sample_size}
              accuracy={initial.accuracy_percentage}
            />
            <div className="score-change">
              <span>{t('accuracyChange')}</span>
              <strong>
                {data.accuracy_change_percentage_points == null
                  ? t('notAvailable')
                  : `${data.accuracy_change_percentage_points > 0 ? '+' : ''}${data.accuracy_change_percentage_points} pp`}
              </strong>
            </div>
            <Score
              title={t('followupAccuracy')}
              correct={followup.correct_answers}
              sample={followup.sample_size}
              accuracy={followup.accuracy_percentage}
            />
          </div>
          </>
        ) : (
          <EmptyState title={t('noProgressData')} />
        )}
        <p className="muted-note">{t('observedOnly')}</p>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t('followupQueue')}</p>
            <h2>{t('studentsNeedingSupport')}</h2>
          </div>
        </div>
        {data.students_needing_support.length ? (
          <div className="support-list">
            {data.students_needing_support.map((student) => (
              <article
                className="support-row"
                key={`${student.student_id}:${student.misconception_code}`}
              >
                <div>
                  <strong>{student.student_code}</strong>
                  <span>
                    <span className="code-pill">
                      {student.misconception_code}
                    </span>
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
    </div>
  );
}
