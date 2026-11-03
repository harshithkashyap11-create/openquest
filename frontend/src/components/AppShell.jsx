import ActiveIndicator from '../motion/ActiveIndicator';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  BookOpenCheck,
  ChartNoAxesCombined,
  ClipboardList,
  GraduationCap,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  RefreshCw,
  UsersRound,
} from 'lucide-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import { listDemoClasses } from '../services/classpulseApi';
import LanguageSelector from './LanguageSelector';
import { lazy, Suspense } from 'react';
import EffectsControl from './EffectsControl';
import MobileDrawer from './ui/MobileDrawer';
import RouteTransition from '../motion/RouteTransition';
const TeacherCopilot = lazy(() => import('./TeacherCopilot'));

export default function AppShell({ role }) {
  const { session, startSession, endSession } = useDemoSession();
  const { t } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotLoaded, setCopilotLoaded] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('classpulse.sidebar') === 'collapsed';
    } catch {
      return false;
    }
  });
  function toggleSidebar() {
    setCollapsed((current) => {
      const next = !current;
      try {
        localStorage.setItem(
          'classpulse.sidebar',
          next ? 'collapsed' : 'expanded',
        );
      } catch {}
      return next;
    });
  }
  const navigate = useNavigate();
  const location = useLocation();
  const routeNotice = location.state?.notice || '';
  const [backendStatus, setBackendStatus] = useState('connecting');
  const [retryHealth, setRetryHealth] = useState(0);
  const mounted = useRef(false);
  const isTeacher = role === 'teacher';
  const links = isTeacher
    ? [
        {
          to: '/teacher/overview',
          label: t('teacherOverview'),
          icon: Activity,
        },
        { to: '/teacher/quizzes', label: t('quizzes'), icon: BookOpenCheck },
        {
          to: '/teacher/insights',
          label: t('classInsights'),
          icon: ChartNoAxesCombined,
        },
        {
          to: '/teacher/interventions#groups',
          label: t('learningGroups'),
          icon: UsersRound,
        },
        {
          to: '/teacher/interventions#assignments',
          label: t('interventions'),
          icon: ClipboardList,
        },
        {
          to: '/teacher/progress',
          label: t('classProgress'),
          icon: ChartNoAxesCombined,
        },
      ]
    : [
        {
          to: '/student/dashboard',
          label: t('studentHome'),
          icon: GraduationCap,
        },
        { to: '/student/quizzes', label: t('quizzes'), icon: BookOpenCheck },
        {
          to: '/student/assessment',
          label: t('assessment'),
          icon: ClipboardList,
        },
        {
          to: '/student/interventions',
          label: t('interventions'),
          icon: UsersRound,
        },
        {
          to: '/student/progress',
          label: t('myProgress'),
          icon: ChartNoAxesCombined,
        },
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

  const routeLabel =
    links.find((item) => item.to === location.pathname + location.hash)
      ?.label ||
    links.find((item) => item.to.split('#')[0] === location.pathname)?.label ||
    t('brand');
  useEffect(() => {
    document.title = `${t('brand')} AI — ${routeLabel}`;
  }, [routeLabel, t]);

  function navigation(mobile = false) {
    return (
      <>
        <Link
          className="brand-lockup"
          to={isTeacher ? '/teacher/overview' : '/student/dashboard'}
          aria-label={`${t('brand')} AI`}
          onClick={() => setMenuOpen(false)}
        >
          <span className="brand-mark" aria-hidden="true">
            <Activity size={22} />
          </span>
          <span className="brand-copy">
            <strong>
              {t('brand')} <em>AI</em>
            </strong>
            <small>{t('brandTagline')}</small>
          </span>
        </Link>
        <div className="sidebar-label">
          {isTeacher ? t('teacherView') : t('studentView')}
        </div>
        <nav
          className="side-nav"
          aria-label={isTeacher ? t('teacher') : t('student')}
        >
          <ActiveIndicator
            value={location.pathname + location.hash}
            selector='[aria-current="page"]'
          />
          {links.map(({ to, label, icon: Icon }) => {
            const active =
              location.pathname === to.split('#')[0] &&
              (!to.includes('#') ||
                location.hash === to.slice(to.indexOf('#')) ||
                (!location.hash && to.endsWith('#groups')));
            return (
              <Link
                key={to}
                to={to}
                className={`nav-link ${active ? 'active' : ''}`}
                aria-current={active ? 'page' : undefined}
                title={collapsed && !mobile ? label : undefined}
                onClick={() => setMenuOpen(false)}
              >
                <Icon size={20} aria-hidden="true" />
                <span className="nav-label">{label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="demo-chip">{t('demoNotice')}</div>
          <button
            className="nav-link signout-button"
            onClick={signOut}
            title={collapsed && !mobile ? t('signOut') : undefined}
          >
            <LogOut size={20} aria-hidden="true" />
            <span className="nav-label">{t('signOut')}</span>
          </button>
          {!mobile && (
            <button
              className="nav-link sidebar-collapse"
              onClick={toggleSidebar}
              aria-expanded={!collapsed}
              aria-label={
                collapsed ? t('expandNavigation') : t('collapseNavigation')
              }
              title={
                collapsed ? t('expandNavigation') : t('collapseNavigation')
              }
            >
              {collapsed ? (
                <PanelLeftOpen size={20} aria-hidden="true" />
              ) : (
                <PanelLeftClose size={20} aria-hidden="true" />
              )}
              <span className="nav-label">{t('collapseNavigation')}</span>
            </button>
          )}
        </div>
      </>
    );
  }

  function signOut() {
    endSession();
    navigate('/login', { replace: true });
  }

  return (
    <div
      className={`app-shell role-${role}${collapsed ? ' sidebar-collapsed' : ''}`}
    >
      <a className="skip-link" href="#main-content">
        {t('skipToMain')}
      </a>
      <aside className="sidebar">{navigation()}</aside>
      <MobileDrawer
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        title={t('navigation')}
      >
        <div className="mobile-navigation">{navigation(true)}</div>
      </MobileDrawer>

      <div className="main-column">
        <header className="topbar">
          <button
            className="icon-button mobile-menu-trigger"
            aria-label={t('openNavigation')}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={21} aria-hidden="true" />
          </button>
          <div className="topbar-class">
            <span className="topbar-dot" aria-hidden="true" />
            {isTeacher ? (
              <span>
                <strong>{session?.className || t('classLabel')}</strong>
                <small>
                  {session?.subject} · {session?.topic}
                </small>
              </span>
            ) : (
              <span>{session?.studentCode}</span>
            )}
          </div>
          <div
            className={`backend-status backend-${backendStatus}`}
            role="status"
            aria-live="polite"
          >
            <span className="backend-status-dot" aria-hidden="true" />
            {backendStatus === 'connected'
              ? t('backendConnected')
              : backendStatus === 'unreachable'
                ? t('backendUnreachable')
                : t('backendConnecting')}
          </div>
          <div className="topbar-controls">
            <EffectsControl />
            <LanguageSelector compact />
            {isTeacher && (
              <button
                className="button button-secondary copilot-launch"
                onClick={() => {
                  setCopilotLoaded(true);
                  setCopilotOpen(true);
                }}
                aria-label={t('openCopilot')}
              >
                <Sparkles size={17} aria-hidden="true" />
                <span>{t('copilot')}</span>
              </button>
            )}
          </div>
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
              {routeNotice === 'teacher'
                ? t('teacherOnlyNotice')
                : t('studentOnlyNotice')}
            </p>
          )}
          <RouteTransition>
            <Outlet />
          </RouteTransition>
        </main>
      </div>
      {isTeacher && session && copilotLoaded && (
        <Suspense fallback={null}>
          <TeacherCopilot
            session={session}
            startSession={startSession}
            open={copilotOpen}
            onDismiss={() => setCopilotOpen(false)}
          />
        </Suspense>
      )}
    </div>
  );
}
