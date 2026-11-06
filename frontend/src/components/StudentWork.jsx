import { useCallback } from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import useAsyncData from '../hooks/useAsyncData';
import { useI18n } from '../i18n/useI18n';
import api from '../services/api';
import { studentQuizzes } from '../services/quizApi';
import { buildStudentWork } from '../services/studentWork';

export default function StudentWork({ studentId }) {
  const { t } = useI18n();
  const load = useCallback(async () => {
    const results = await Promise.allSettled([
      studentQuizzes(studentId),
      api.get(`/students/${studentId}/studio/activities`).then(response => response.data),
      api.get(`/students/${studentId}/inclusive/lessons`).then(response => response.data),
    ]);
    const values = results.map(result => result.status === 'fulfilled' ? result.value : []);
    return { items: buildStudentWork({ quizzes: values[0], activities: values[1], lessons: values[2] }), unavailable: results.some(result => result.status === 'rejected') };
  }, [studentId]);
  const { data, loading, refreshing, reload } = useAsyncData(load, studentId);
  return <section className="panel" aria-labelledby="student-work-title">
    <div className="panel-heading"><div><p className="eyebrow">{t('keepLearning')}</p><h2 id="student-work-title">{t('studentWorkTitle')}</h2></div><button className="button button-secondary" onClick={reload} disabled={loading || refreshing}>{t('refresh')}</button></div>
    {loading ? <p role="status">{t('loading')}</p> : <>
      {data.unavailable && <p role="status" className="muted-note">{t('studentWorkUnavailable')}</p>}
      {data.items.length ? <div className="completed-list">{data.items.map(item => <Link key={`${item.kind}:${item.id}`} to={item.href}><span><strong>{item.title}</strong><br /><small>{t(`studentWork_${item.kind}`)}</small></span><ArrowRight size={18} aria-hidden="true" /></Link>)}</div> : !data.unavailable && <p>{t('studentWorkEmpty')}</p>}
    </>}
  </section>;
}
