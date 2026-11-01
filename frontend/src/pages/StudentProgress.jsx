import { ArrowDownRight, ArrowUpRight, ChartNoAxesCombined } from 'lucide-react';
import { useCallback } from 'react';
import MetricCard from '../components/MetricCard';
import PageHeader from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/PageStates';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { getStudentProgress } from '../services/classpulseApi';

export default function StudentProgress() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const loadProgress = useCallback(
    () => getStudentProgress(session.studentId),
    [session.studentId],
  );
  const { data, loading, error, reload } = useAsyncData(
    loadProgress,
    session.studentId,
  );

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const change = data.accuracy_change_percentage_points;
  return (
    <div className="page-content">
      <PageHeader
        eyebrow={t('progressEyebrow')}
        title={t('yourProgress')}
        description={t('progressDescription')}
      />
      <section className="metric-grid metric-grid-three">
        <MetricCard label={t('activitiesAssigned')} value={data.assigned_interventions} />
        <MetricCard label={t('activitiesCompleted')} value={data.completed_interventions} />
        <MetricCard label={t('reassessmentsCompleted')} value={data.completed_reassessments} icon={ChartNoAxesCombined} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div><p className="eyebrow">{t('yourProgress')}</p><h2>{t('scoreComparison')}</h2></div>
          {change != null && (
            <span className={`change-badge ${change >= 0 ? 'change-positive' : 'change-negative'}`}>
              {change >= 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
              {change > 0 ? '+' : ''}{change} pp
            </span>
          )}
        </div>
        {data.initial_assessment.sample_size || data.followup_assessment.sample_size ? (
          <>
            <div className="score-comparison">
              <Score
                title={t('initialAccuracy')}
                accuracy={data.initial_assessment.accuracy_percentage}
                correct={data.initial_assessment.correct_answers}
                sample={data.initial_assessment.sample_size}
              />
              <div className="score-change">
                <span>{t('accuracyChange')}</span>
                <strong>{change == null ? t('notAvailable') : `${change > 0 ? '+' : ''}${change} pp`}</strong>
              </div>
              <Score
                title={t('followupAccuracy')}
                accuracy={data.followup_assessment.accuracy_percentage}
                correct={data.followup_assessment.correct_answers}
                sample={data.followup_assessment.sample_size}
              />
            </div>
            <p className="muted-note">{t('observedOnly')}</p>
          </>
        ) : (
          <EmptyState title={t('noProgressData')} />
        )}
      </section>
    </div>
  );
}

function Score({ title, accuracy, correct, sample }) {
  const { t } = useI18n();
  return (
    <div className="score-tile">
      <span>{title}</span>
      <strong>{accuracy == null ? t('notAvailable') : `${accuracy}%`}</strong>
      <small>
        {sample ? `${correct} / ${sample} ${t('observations')}` : t('notTakenYet')}
      </small>
    </div>
  );
}
