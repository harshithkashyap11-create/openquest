import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { Activity, ArrowUpRight, BookOpen, LogOut } from 'lucide-react';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import LanguageSelector from '../components/LanguageSelector';
import Button from '../components/ui/Button';
import '../styles/studio.css';

export default function Courses() {
  const { session, startSession, endSession } = useDemoSession(); const { t } = useI18n(); const navigate = useNavigate();
  const [query, setQuery] = useState(''); const [error, setError] = useState('');
  if (!session) return <Navigate to="/login" replace />;
  const courses = session.courses || session.classes || [];
  function open(c) {
    startSession({ ...session, classId: c.id, className: c.class_name, subject: c.subject, topic: c.topic, studentId: c.student_id || session.studentId, studentCode: c.student_code || session.studentCode });
    navigate(session.role === 'teacher' ? '/teacher/overview' : '/student/dashboard');
  }
  return <main className="courses-page">
    <header className="courses-topbar"><a className="brand-lockup" href="/courses"><span className="brand-mark"><Activity size={22} aria-hidden="true" /></span><strong>{t('brand')} AI</strong></a><div className="studio-actions"><LanguageSelector compact /><Button variant="secondary" onClick={async () => { try { await endSession(); navigate('/login'); } catch(e) { setError(e.message); } }}><LogOut size={16} aria-hidden="true" />{t('signOut')}</Button></div></header>
    <section className="courses-content"><p className="eyebrow">{t(session.role)} · {session.username || session.studentCode || t('brand')}</p><h1>{t('myCourses')}</h1><p className="studio-muted">{t('coursePickerHelp')}</p>
      <label htmlFor="course-search" className="sr-only">{t('searchCourses')}</label><input className="course-search" id="course-search" placeholder={t('searchCourses')} value={query} onChange={e => setQuery(e.target.value)} />
      {error && <p className="form-error" role="alert">{error}</p>}
      {[...new Set(courses.map(c => c.subject))].map(subject => {
        const shown = courses.filter(c => c.subject === subject && `${c.subject} ${c.topic} ${c.class_name}`.toLowerCase().includes(query.toLowerCase()));
        return shown.length ? <section className="course-subject" key={subject}><h2>{subject}</h2><div className="course-grid">{shown.map(c => <button type="button" className="course-card" aria-label={`${t('openCourse')} ${c.topic}`} key={c.id} onClick={() => open(c)}><BookOpen size={28} aria-hidden="true" /><span className="course-card-text"><strong>{c.topic}</strong><small>{subject}</small></span><ArrowUpRight size={22} aria-hidden="true" /></button>)}</div></section> : null;
      })}
      {!courses.some(c => `${c.subject} ${c.topic} ${c.class_name}`.toLowerCase().includes(query.toLowerCase())) && <p>{t('noCoursesFound')}</p>}
    </section>
  </main>;
}
