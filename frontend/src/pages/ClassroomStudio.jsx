import { useCallback } from 'react';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { ErrorState, LoadingState } from '../components/PageStates';
import api from '../services/api';
import TeacherStudio from './TeacherStudio';
import StudentStudio from './StudentStudio';
import '../styles/studio.css';

export default function ClassroomStudio() {
  const { session } = useDemoSession();
  return <StudioCourse key={`${session.role}:${session.classId}:${session.studentId || ''}`} session={session} />;
}

function StudioCourse({ session }) {
  const { t } = useI18n(); const teacher = session.role === 'teacher';
  const root = teacher ? `/classes/${session.classId}/studio` : `/students/${session.studentId}/studio`;
  const load = useCallback(async () => (await api.get(root + '/activities')).data, [root]);
  const { data, loading, error, reload } = useAsyncData(load, root);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return <div className="studio-page"><header className="studio-heading"><div><p className="eyebrow">{session.subject} · {session.topic}</p><h1>{t('classroomStudio')}</h1><p className="studio-muted">{t(teacher ? 'studioTeacherHelp' : 'studioStudentHelp')}</p></div></header>
    {teacher ? <TeacherStudio activities={data || []} reload={reload} root={root} session={session} /> : <StudentStudio activities={data || []} reload={reload} root={root} />}
  </div>;
}
