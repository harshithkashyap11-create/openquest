import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, BookOpenCheck, GraduationCap, Check } from 'lucide-react';
import useAsyncData from '../hooks/useAsyncData';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import LanguageSelector from '../components/LanguageSelector';
import Button from '../components/ui/Button';
import { ErrorState, LoadingState } from '../components/PageStates';
import api, { getErrorMessage } from '../services/api';

async function config() { return (await api.get('/auth/config')).data; }

export default function Login() {
  const { data, loading, error, reload } = useAsyncData(config, 'auth-config');
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return <SignIn demo={data.mode === 'demo'} />;
}

function SignIn({ demo }) {
  const { t } = useI18n(); const { startSession } = useDemoSession(); const navigate = useNavigate();
  const [role, setRole] = useState('teacher'); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    try {
      const payload = { username: form.get('username'), password: form.get('password'), ...(demo ? { role } : {}) };
      const result = (await api.post(demo ? '/auth/demo-login' : '/auth/login', payload)).data;
      const courses = result.courses || result.classes.map(c => ({ ...c, student_id: result.studentId, student_code: result.studentCode }));
      startSession({ ...result, courses });
      navigate('/courses', { replace: true });
    } catch (e) { setError(getErrorMessage(e)); }
    finally { setBusy(false); }
  }
  return <main className="entry-page">
    <header className="entry-topbar"><a className="brand-lockup" href="/"><span className="brand-mark"><Activity size={22} aria-hidden="true" /></span><span><strong>{t('brand')} <em>AI</em></strong><small>{t('brandTagline')}</small></span></a><LanguageSelector compact /></header>
    <section className="entry-content" aria-labelledby="entry-title">
      <div className="entry-copy"><p className="eyebrow">{t('entryEyebrow')}</p><h1 id="entry-title">{t('entryValue')}</h1><p>{t('courseEntryDescription')}</p>
        <div className="course-entry-steps"><p><span>01</span>{t('accountSignIn')}</p><p><span>02</span>{t('chooseCourse')}</p><p><span>03</span>{t('courseBegin')}</p></div>
        {demo && <p className="entry-note">{t('syntheticData')}</p>}
      </div>
      <section className="entry-card" aria-labelledby="signin-title"><p className="eyebrow">{demo ? t('demoAccount') : t('accountSignIn')}</p><h2 id="signin-title">{t('courseWelcome')}</h2>
        {demo && <div className="role-picker" aria-label={t('loginSubtitle')}>{[['teacher', BookOpenCheck], ['student', GraduationCap]].map(([value, Icon]) => <button key={value} type="button" aria-label={t(value)} aria-pressed={role === value} className={`role-option ${role === value ? 'selected' : ''}`} onClick={() => { setRole(value); setError(''); }}><Icon size={24} aria-hidden="true" /><strong>{t(value)}</strong>{role === value && <Check size={16} className="role-check" aria-hidden="true" />}</button>)}</div>}
        <form className="entry-form" onSubmit={submit}>
          <label htmlFor="account-user">{t('username')}</label><input key={role} id="account-user" name="username" autoComplete="username" placeholder={demo ? role === 'teacher' ? 'math1' : 'S1' : ''} required maxLength={100} aria-describedby={demo ? 'demo-login-help' : undefined} />
          <label htmlFor="account-password">{t('password')}</label><input id="account-password" name="password" type="password" autoComplete="current-password" required maxLength={256} aria-describedby={demo ? 'demo-password-help' : undefined} />
          {demo && <><p id="demo-login-help" className="field-help">{t(role === 'teacher' ? 'demoTeacherAccounts' : 'demoStudentAccounts')}</p><p id="demo-password-help" className="field-help">{t('anyDemoPassword')}</p></>}
          {error && <p role="alert" className="form-error">{error}</p>}
          <Button type="submit" busy={busy} size="lg" className="button-wide">{t('accountSignIn')}<ArrowRight size={17} aria-hidden="true" /></Button>
        </form>
      </section>
    </section>
  </main>;
}
