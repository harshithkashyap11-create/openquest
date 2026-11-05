import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BookOpenCheck,
  GraduationCap,
  ShieldCheck,
  Activity,
  Check,
  ArrowRight,
  ScanSearch,
  UsersRound,
  Sprout,
  ChartNoAxesCombined,
} from 'lucide-react';
import useAsyncData from '../hooks/useAsyncData';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import LanguageSelector from '../components/LanguageSelector';
import Button from '../components/ui/Button';
import { ErrorState, LoadingState } from '../components/PageStates';
import { getErrorMessage } from '../services/api';
import { classDisplayName } from '../services/classDisplayName';
import api from '../services/api';
import {
  listDemoClasses,
  listDemoStudents,
  resolveStudent,
} from '../services/classpulseApi';

export default function Login() {
  const { data, loading, error, reload } = useAsyncData(loadAuthConfig, 'auth-config');
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return data.mode === 'required' ? <AccountLogin /> : <DemoLogin />;
}

async function loadAuthConfig() { return (await api.get('/auth/config')).data; }

function AccountLogin() {
  const { t } = useI18n();
  const { startSession } = useDemoSession();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    try {
      const result = (await api.post('/auth/login', { username: form.get('username'), password: form.get('password') })).data;
      const classroom = result.classes[0];
      if (!classroom) throw new Error(t('noClasses'));
      startSession({ ...result, classId: classroom.id, className: classroom.class_name, subject: classroom.subject, topic: classroom.topic });
      navigate(result.role === 'teacher' ? '/teacher/overview' : '/student/dashboard', { replace: true });
    } catch (e) { setError(e.response ? getErrorMessage(e) : e.message); }
    finally { setBusy(false); }
  }
  return <main className="entry-page"><section className="entry-card" style={{ margin: '4rem auto', maxWidth: '28rem' }}>
    <LanguageSelector /><h1>{t('brand')} · {t('accountSignIn')}</h1>
    <form className="entry-form" onSubmit={submit}>
      <label htmlFor="account-user">{t('username')}</label><input id="account-user" name="username" autoComplete="username" required maxLength={100} />
      <label htmlFor="account-password">{t('password')}</label><input id="account-password" name="password" type="password" autoComplete="current-password" required maxLength={256} />
      {error && <p role="alert" className="form-error">{error}</p>}
      <Button type="submit" busy={busy}>{t('accountSignIn')}</Button>
    </form></section></main>;
}

function DemoLogin() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { startSession } = useDemoSession();
  const {
    data: classes,
    loading,
    error,
    reload,
  } = useAsyncData(listDemoClasses, 'demo-classes');
  const [role, setRole] = useState('teacher');
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [classId, setClassId] = useState('');
  const [studentCode, setStudentCode] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const loadRoster = useCallback(
    () => (classId ? listDemoStudents(classId) : Promise.resolve([])),
    [classId],
  );
  const {
    data: roster = [],
    loading: rosterLoading,
    error: rosterError,
    reload: reloadRoster,
  } = useAsyncData(loadRoster, classId);

  const availableClasses = classes || [];
  const availableSubjects = [
    ...new Set(availableClasses.map((item) => item.subject)),
  ];
  const subjectClasses = availableClasses.filter(
    (item) => item.subject === subject,
  );
  const availableTopics = [
    ...new Set(subjectClasses.map((item) => item.topic)),
  ];
  const topicClasses = subjectClasses.filter((item) => item.topic === topic);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitError('');
    if (
      !subject ||
      !topic ||
      !classId ||
      (role === 'student' && !studentCode.trim())
    ) {
      setSubmitError(t('requiredField'));
      return;
    }

    if (role === 'teacher') {
      const selectedClass = availableClasses.find(
        (item) => item.id === classId,
      );
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
      const selectedClass = availableClasses.find(
        (item) => item.id === classId,
      );
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
            <Activity size={22} />
          </span>
          <span>
            <strong>
              {t('brand')} <em>AI</em>
            </strong>
            <small>{t('brandTagline')}</small>
          </span>
        </a>
        <div className="entry-preferences">
          <LanguageSelector compact />
        </div>
      </header>

      <section className="entry-content" aria-labelledby="entry-title">
        <div className="entry-copy">
          <p className="eyebrow">
            <span className="entry-kicker-line" />
            {t('entryEyebrow')}
          </p>
          <h1 id="entry-title">{t('entryValue')}</h1>
          <p>{t('entryDescription')}</p>
          <div className="learning-loop" aria-label={t('entryLoopTitle')}>
            {[
              ['loopDiagnose', ScanSearch],
              ['loopGroup', UsersRound],
              ['loopIntervene', Sprout],
              ['loopReassess', ChartNoAxesCombined],
            ].map(([key, Icon], index) => (
              <div className="loop-step" key={key}>
                <span className="loop-number">0{index + 1}</span>
                <span className="loop-icon">
                  <Icon size={22} strokeWidth={1.6} aria-hidden="true" />
                </span>
                <strong>{t(key)}</strong>
              </div>
            ))}
          </div>
          <div className="entry-subjects">
            {availableSubjects.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          <div className="entry-note">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>
              {t('syntheticData')}
            </span>
          </div>
        </div>

        <section className="entry-card" aria-labelledby="entry-workspace-title">
          <div className="entry-card-heading">
            <p className="eyebrow">{t('entryStep')}</p>
            <h2 id="entry-workspace-title">{t('entryWorkspace')}</h2>
            <p>{t('entryWorkspaceHelp')}</p>
          </div>
          <div className="role-picker" aria-label={t('loginSubtitle')}>
            <button
              type="button"
              className={
                role === 'teacher' ? 'role-option selected' : 'role-option'
              }
              aria-pressed={role === 'teacher'}
              onClick={() => {
                setRole('teacher');
                setSubmitError('');
              }}
            >
              <BookOpenCheck size={25} strokeWidth={1.7} aria-hidden="true" />
              <strong>{t('teacher')}</strong>
              <small>{t('entryTeacherDescription')}</small>
              {role === 'teacher' && (
                <Check size={16} className="role-check" aria-hidden="true" />
              )}
            </button>
            <button
              type="button"
              className={
                role === 'student' ? 'role-option selected' : 'role-option'
              }
              aria-pressed={role === 'student'}
              onClick={() => {
                setRole('student');
                setSubmitError('');
              }}
            >
              <GraduationCap size={25} strokeWidth={1.7} aria-hidden="true" />
              <strong>{t('student')}</strong>
              <small>{t('entryStudentDescription')}</small>
              {role === 'student' && (
                <Check size={16} className="role-check" aria-hidden="true" />
              )}
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
                  <option value={item} key={item}>
                    {item}
                  </option>
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
                      <option value={item} key={item}>
                        {item}
                      </option>
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
                        {classDisplayName(item.class_name, item.topic)} · {item.student_count} {t('students')}
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
                    name="student-code"
                    spellCheck={false}
                    autoComplete="off"
                    list="demo-student-codes"
                    value={studentCode}
                    onChange={(event) => setStudentCode(event.target.value)}
                    aria-describedby="student-code-help"
                    required
                  />
                  <datalist id="demo-student-codes">
                    {(roster ?? []).map((student) => (
                      <option
                        key={student.student_id}
                        value={student.student_code}
                      />
                    ))}
                  </datalist>
                  {rosterLoading && (
                    <span className="field-help" role="status">
                      {t('loading')}
                    </span>
                  )}
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
              <Button
                type="submit"
                size="lg"
                className="button-wide"
                busy={submitting}
              >
                {submitting
                  ? t('loadingShort')
                  : role === 'teacher'
                    ? t('continueAsTeacher')
                    : t('continueAsStudent')}
                <ArrowRight size={17} aria-hidden="true" />
              </Button>
            </form>
          )}
        </section>
      </section>
    </main>
  );
}
