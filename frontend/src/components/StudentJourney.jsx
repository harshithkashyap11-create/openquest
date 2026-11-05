import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { studentJourney } from '../services/learningApi';
import { EmptyState, ErrorState, LoadingState } from './PageStates';
import '../pages/MisconceptionMap.css';

export function JourneyNavigation() {
  const { t } = useI18n();
  return <nav aria-label={t('mapJourney')}><ol className="journey-nav">
    {[
      ['/student/assessment', 'assessment'],
      ['/student/interventions', 'mapStepPractice'],
      ['/student/interventions', 'mapStepReassessment'],
      ['/student/progress', 'mapResults'],
    ].map(([url, key], index) => <li key={key}><Link to={url}>{index + 1}. {t(key)}</Link></li>)}
  </ol></nav>;
}

export default function StudentJourney({ studentId }) {
  const { t, language } = useI18n();
  const [offset, setOffset] = useState(0);
  const load = useCallback(() => studentJourney(studentId, { offset, limit: 30 }), [studentId, offset]);
  const { data, loading, error, reload } = useAsyncData(load, `${studentId}:${offset}`);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={t('mapJourneyFailed')} error={error} onRetry={reload} />;
  return <section className="panel" aria-labelledby="journey-title">
    <h2 id="journey-title">{t('mapJourney')}</h2>
    <p>{t('mapJourneyHelp')}</p>
    {!data.events.length ? <EmptyState title={t('mapJourneyEmpty')} /> : <ol className="journey-events" start={offset + 1}>
      {data.events.map(event => <li key={`${event.kind}:${event.source_id}`}>
        <strong>{t(`mapEvent_${event.kind}`)}</strong>
        <time dateTime={event.at}>{new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' }).format(new Date(event.at))}</time>
        {event.question_text && <p>{event.question_text}</p>}
        {event.answer != null && <p>{t('mapStudentResponse')}: {event.answer || t('noAnswer')}</p>}
        {event.title && <p>{event.title} · {t(event.status)}</p>}
        {event.total != null && <p>{t('mapScore', { correct: event.correct, total: event.total })}</p>}
        {event.assignment_id && <Link to={`/student/interventions/${event.assignment_id}`}>{t('openActivity')}</Link>}
      </li>)}
    </ol>}
    <p>{t('mapJourneyGaps')}</p>
    <div className="learning-actions">
      <button className="button button-secondary" disabled={offset === 0} onClick={() => setOffset(x => Math.max(0, x - 30))}>{t('mapPreviousPage')}</button>
      <span>{t('mapPageCount', { from: data.total ? offset + 1 : 0, to: Math.min(offset + 30, data.total), total: data.total })}</span>
      <button className="button button-secondary" disabled={offset + 30 >= data.total} onClick={() => setOffset(x => x + 30)}>{t('mapNextPage')}</button>
    </div>
  </section>;
}
