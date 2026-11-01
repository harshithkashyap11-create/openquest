import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpenCheck, GraduationCap, ShieldCheck } from 'lucide-react';
import useAsyncData from '../hooks/useAsyncData';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import LanguageSelector from '../components/LanguageSelector';
import { ErrorState, LoadingState } from '../components/PageStates';
import { getErrorMessage } from '../services/api';
import {
  listDemoClasses,
  listDemoStudents,
  resolveStudent,
} from '../services/classpulseApi';

export default function Login() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { startSession } = useDemoSession();
  const { data: classes, loading, error, reload } = useAsyncData(
    listDemoClasses,
    'demo-classes',
  );
  const [role, setRole] = useState('teacher');
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [classId, setClassId] = useState('');
  const [studentCode, setStudentCode] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const loadRoster = useCallback(
    () => classId ? listDemoStudents(classId) : Promise.resolve([]),
    [classId],
  );
  const {
    data: roster = [],
    loading: rosterLoading,
    error: rosterError,
    reload: reloadRoster,
  } = useAsyncData(loadRoster, classId);

  const availableClasses = classes || [];
  const availableSubjects = [...new Set(availableClasses.map((item) => item.subject))];
  const subjectClasses = availableClasses.filter((item) => item.subject === subject);
  const availableTopics = [...new Set(subjectClasses.map((item) => item.topic))];
  const topicClasses = subjectClasses.filter((item) => item.topic === topic);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitError('');
    if (!subject || !topic || !classId || (role === 'student' && !studentCode.trim())) {
      setSubmitError(t('requiredField'));
      return;
    }

    if (role === 'teacher') {
      const selectedClass = availableClasses.find((item) => item.id === classId);
      startSession({
        role,
        classId,
        className: selectedClass?.class_name || '',
        subject,
        topic,
      });
      navigate('/teacher/overview', { replace: true });
      return;
    }

    setSubmitting(true);
    try {
      const student = await resolveStudent(classId, studentCode);
      const selectedClass = availableClasses.find((item) => item.id === classId);
      startSession({
        role,
        studentId: student.student_id,
        studentCode: student.student_code,
        classId: student.class_id,
        className: selectedClass?.class_name || '',
        subject,
        topic,
      });
      navigate('/student/dashboard', { replace: true });
    } catch (resolveError) {
      setSubmitError(getErrorMessage(resolveError, t('connectionError')));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="entry-page">
      <header className="entry-topbar">
        <a className="brand-lockup" href="/">
          <span className="brand-mark" aria-hidden="true">
            <BookOpenCheck size={20} />
          </span>
          <span>
            <strong>{t('brand')}</strong>
            <small>{t('brandTagline')}</small>
          </span>
        </a>
        <LanguageSelector />
      </header>

      <section className="entry-content" aria-labelledby="entry-title">
        <div className="entry-copy">
          <p className="eyebrow">{t('brandTagline')}</p>
          <h1 id="entry-title">{t('loginTitle')}</h1>
          <p>{t('loginSubtitle')}</p>
          <div className="entry-note">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>{t('demoNotice')}</span>
          </div>
        </div>

        <section className="entry-card">
          <div className="role-picker" aria-label={t('loginSubtitle')}>
            <button
              type="button"
              className={role === 'teacher' ? 'role-option selected' : 'role-option'}
              aria-pressed={role === 'teacher'}
              onClick={() => {
                setRole('teacher');
                setSubmitError('');
              }}
            >
              <BookOpenCheck size={18} aria-hidden="true" />
              {t('teacher')}
            </button>
            <button
              type="button"
              className={role === 'student' ? 'role-option selected' : 'role-option'}
              aria-pressed={role === 'student'}
              onClick={() => {
                setRole('student');
                setSubmitError('');
              }}
            >
              <GraduationCap size={18} aria-hidden="true" />
              {t('student')}
            </button>
          </div>

          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState error={error} onRetry={reload} />
          ) : availableClasses.length === 0 ? (
            <p className="inline-empty">{t('noClasses')}</p>
          ) : (
            <form className="entry-form" onSubmit={handleSubmit}>
              <label htmlFor="demo-subject">{t('chooseSubject')}</label>
              <select
                id="demo-subject"
                required
                value={subject}
                onChange={(event) => {
                  setSubject(event.target.value);
                  setTopic('');
                  setClassId('');
                  setStudentCode('');
                }}
              >
                <option value="">{t('chooseSubject')}</option>
                {availableSubjects.map((item) => (
                  <option value={item} key={item}>{item}</option>
                ))}
              </select>

              {subject && (
                <>
                  <label htmlFor="demo-topic">{t('chooseTopic')}</label>
                  <select
                    id="demo-topic"
                    required
                    value={topic}
                    onChange={(event) => {
                      setTopic(event.target.value);
                      setClassId('');
                      setStudentCode('');
                    }}
                  >
                    <option value="">{t('chooseTopic')}</option>
                    {availableTopics.map((item) => (
                      <option value={item} key={item}>{item}</option>
                    ))}
                  </select>
                </>
              )}

              {topic && (
                <>
              <label htmlFor="demo-class">{t('chooseClass')}</label>
              <select
                id="demo-class"
                required
                value={classId}
                onChange={(event) => {
                  setClassId(event.target.value);
                  setStudentCode('');
                }}
              >
                <option value="">{t('chooseClass')}</option>
                {topicClasses.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.class_name} · {item.student_count} {t('students')}
                  </option>
                ))}
              </select>
                </>
              )}

              {role === 'student' && classId && (
                <div className="field-stack">
                  <label htmlFor="student-code">{t('studentCode')}</label>
                  <input
                    id="student-code"
                    autoComplete="off"
                    list="demo-student-codes"
                    value={studentCode}
                    onChange={(event) => setStudentCode(event.target.value)}
                    aria-describedby="student-code-help"
                    required
                  />
                  <datalist id="demo-student-codes">
                    {(roster ?? []).map((student) => (
                      <option key={student.student_id} value={student.student_code} />
                    ))}
                  </datalist>
                  {rosterLoading && <span className="field-help" role="status">{t('loading')}</span>}
                  {rosterError && (
                    <div className="form-error" role="alert">
                      <span>{t('rosterUnavailable')}</span>
                      <button
                        type="button"
                        className="text-link"
                        onClick={reloadRoster}
                      >
                        {t('retry')}
                      </button>
                    </div>
                  )}
                  <span id="student-code-help" className="field-help">
                    {t('studentCodeHelp')}
                  </span>
                </div>
              )}

              {submitError && (
                <p className="form-error" role="alert">
                  {submitError}
                </p>
              )}
              <button
                type="submit"
                className="button button-primary button-wide"
                disabled={submitting}
              >
                {submitting
                  ? t('loadingShort')
                  : role === 'teacher'
                    ? t('continueAsTeacher')
                    : t('continueAsStudent')}
              </button>
            </form>
          )}
        </section>
      </section>
    </main>
  );
}
