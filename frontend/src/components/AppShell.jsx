import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  BookOpenCheck,
  ChartNoAxesCombined,
  ClipboardList,
  GraduationCap,
  LogOut,
  RefreshCw,
  UsersRound,
} from 'lucide-react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import { listDemoClasses } from '../services/classpulseApi';
import LanguageSelector from './LanguageSelector';

export default function AppShell({ role }) {
  const { session, endSession } = useDemoSession();
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const routeNotice = location.state?.notice || '';
  const [backendStatus, setBackendStatus] = useState('connecting');
  const [retryHealth, setRetryHealth] = useState(0);
  const mounted = useRef(false);
  const isTeacher = role === 'teacher';
  const links = isTeacher
    ? [
        { to: '/teacher/overview', label: t('teacherOverview'), icon: Activity },
        { to: '/teacher/insights', label: t('classInsights'), icon: ChartNoAxesCombined },
        { to: '/teacher/interventions#groups', label: t('learningGroups'), icon: UsersRound },
        { to: '/teacher/interventions#assignments', label: t('interventions'), icon: ClipboardList },
        { to: '/teacher/progress', label: t('classProgress'), icon: ChartNoAxesCombined },
      ]
    : [
        { to: '/student/dashboard', label: t('studentHome'), icon: GraduationCap },
        { to: '/student/assessment', label: t('assessment'), icon: ClipboardList },
        { to: '/student/interventions', label: t('interventions'), icon: UsersRound },
        { to: '/student/progress', label: t('myProgress'), icon: ChartNoAxesCombined },
      ];

  const checkBackend = useCallback(async () => {
    try {
      await listDemoClasses();
      if (!mounted.current) return;
      setBackendStatus('connected');
    } catch {
      if (!mounted.current) return;
      setBackendStatus('unreachable');
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    const initialCheck = window.setTimeout(() => void checkBackend(), 0);
    const checkWhileVisible = () => {
      if (document.visibilityState === 'visible') void checkBackend();
    };
    const timer = window.setInterval(checkWhileVisible, 45000);
    document.addEventListener('visibilitychange', checkWhileVisible);
    return () => {
      mounted.current = false;
      window.clearTimeout(initialCheck);
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', checkWhileVisible);
    };
  }, [checkBackend, retryHealth]);

  useEffect(() => {
    const routeLabel = location.pathname.startsWith('/teacher')
      ? location.pathname.includes('insights')
        ? t('classInsights')
        : location.pathname.includes('interventions')
          ? t('interventions')
          : location.pathname.includes('progress')
            ? t('classProgress')
            : t('teacherOverview')
      : location.pathname.includes('assessment')
        ? t('assessment')
        : location.pathname.includes('interventions')
          ? t('interventions')
          : location.pathname.includes('progress')
            ? t('myProgress')
            : t('studentHome');
    document.title = `${t('brand')} — ${routeLabel}`;
    document.querySelector('h1')?.focus({ preventScroll: true });
  }, [location.pathname, language, t]);

  function signOut() {
    endSession();
    navigate('/login', { replace: true });
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">{t('skipToMain')}</a>
      <aside className="sidebar">
        <Link className="brand-lockup" to={isTeacher ? '/teacher/overview' : '/student/dashboard'}>
          <span className="brand-mark" aria-hidden="true">
            <BookOpenCheck size={20} />
          </span>
          <span>
            <strong>{t('brand')}</strong>
            <small>{t('brandTagline')}</small>
          </span>
        </Link>
        <div className="sidebar-label">{isTeacher ? t('teacherView') : t('studentView')}</div>
        <nav className="side-nav" aria-label={isTeacher ? t('teacher') : t('student')}>
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => {
                const hash = to.includes('#') ? to.slice(to.indexOf('#')) : '';
                const active = isActive && (!hash || location.hash === hash);
                return `nav-link ${active ? 'active' : ''}`;
              }}
              aria-current={
                location.pathname === to.split('#')[0]
                && (!to.includes('#') || location.hash === to.slice(to.indexOf('#')))
                  ? 'page'
                  : undefined
              }
            >
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="demo-chip">{t('demoNotice')}</div>
          <button className="nav-link signout-button" onClick={signOut}>
            <LogOut size={18} aria-hidden="true" />
            <span>{t('signOut')}</span>
          </button>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="topbar-class">
            <span className="topbar-dot" aria-hidden="true" />
            {isTeacher ? (
              <span>{session?.className || t('classLabel')}</span>
            ) : (
              <span>{session?.studentCode}</span>
            )}
          </div>
          <div className={`backend-status backend-${backendStatus}`} role="status" aria-live="polite">
            <span className="backend-status-dot" aria-hidden="true" />
            {backendStatus === 'connected'
              ? t('backendConnected')
              : backendStatus === 'unreachable'
                ? t('backendUnreachable')
                : t('backendConnecting')}
          </div>
          <LanguageSelector compact />
        </header>
        {backendStatus === 'unreachable' && (
          <div className="backend-banner" role="alert">
            <span>{t('backendUnavailableMessage')}</span>
            <button
              className="button button-secondary"
              onClick={() => setRetryHealth((value) => value + 1)}
            >
              <RefreshCw size={15} aria-hidden="true" />
              {t('retry')}
            </button>
          </div>
        )}
        <main className="main-panel" id="main-content" tabIndex={-1}>
          {routeNotice && (
            <p className="status-message" role="status">
              {routeNotice === 'teacher' ? t('teacherOnlyNotice') : t('studentOnlyNotice')}
            </p>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
