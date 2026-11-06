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
  Sparkles,
  Sprout,
  RefreshCw,
  UsersRound,
} from 'lucide-react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import { listDemoClasses } from '../services/classpulseApi';
import { classDisplayName } from '../services/classDisplayName';
import LanguageSelector from './LanguageSelector';
import { lazy, Suspense } from 'react';
import MobileDrawer from './ui/MobileDrawer';
import RouteTransition from '../motion/RouteTransition';
const TeacherCopilot = lazy(() => import('./TeacherCopilot'));

export default function AppShell({ role }) {
  const { session, startSession, endSession } = useDemoSession();
  const { t } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
  const [signOutError, setSignOutError] = useState('');
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
  const [classes, setClasses] = useState([]);
  const [retryHealth, setRetryHealth] = useState(0);
  const mounted = useRef(false);
  const isTeacher = role === 'teacher';
  const subjectClasses = session.courses || classes.filter(item => item.subject === (session.teachingSubject || session.subject));
  const links = isTeacher
    ? [
        {
          to: '/teacher/overview',
          label: t('teacherOverview'),
          icon: Activity,
        },
        { to: '/teacher/quizzes', label: t('quizzes'), icon: BookOpenCheck },
        { to: '/teacher/studio', label: t('classroomStudio'), icon: BookOpenCheck },
        { to: '/teacher/map', label: t('mapTitle'), icon: UsersRound },
        { to: '/teacher/guide', label: t('mapGuide'), icon: BookOpenCheck },
        { to: '/teacher/learning', label: t('learningEvidence'), icon: Sprout },
        { to: '/teacher/lessons', label: t('lessonStudio'), icon: BookOpenCheck },
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
        { to: '/student/studio', label: t('classroomStudio'), icon: BookOpenCheck },
        { to: '/student/learning', label: t('learningLab'), icon: Sprout },
        { to: '/student/guide', label: t('mapGuide'), icon: BookOpenCheck },
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
    if (!navigator.onLine) {
      if (mounted.current) setBackendStatus('offline');
      return;
    }
    try {
      const available = await listDemoClasses();
      if (!mounted.current) return;
      setClasses(available);
      setBackendStatus('connected');
    } catch {
      if (!mounted.current) return;
      setBackendStatus(navigator.onLine ? 'unreachable' : 'offline');
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
    window.addEventListener('online', checkWhileVisible);
    window.addEventListener('offline', checkWhileVisible);
    return () => {
      mounted.current = false;
      window.clearTimeout(initialCheck);
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', checkWhileVisible);
      window.removeEventListener('online', checkWhileVisible);
      window.removeEventListener('offline', checkWhileVisible);
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
        <button
          type="button"
          className="brand-lockup"
          aria-label={`${t('brand')} AI · ${t(mobile || !collapsed ? 'collapseNavigation' : 'expandNavigation')}`}
          aria-expanded={mobile ? menuOpen : !collapsed}
          title={t(mobile || !collapsed ? 'collapseNavigation' : 'expandNavigation')}
          onClick={mobile ? () => setMenuOpen(false) : toggleSidebar}
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
        </button>
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
          {session.courses && <Link className="nav-link" to="/courses" onClick={() => setMenuOpen(false)}><GraduationCap size={20} aria-hidden="true" /><span className="nav-label">{t('myCourses')}</span></Link>}
        </nav>
        <div className="sidebar-bottom">
          <button
            className="nav-link signout-button"
            onClick={signOut}
            title={collapsed && !mobile ? t('signOut') : undefined}
          >
            <LogOut size={20} aria-hidden="true" />
            <span className="nav-label">{t(session.authenticated ? 'accountSignOut' : 'signOut')}</span>
          </button>
        </div>
      </>
    );
  }

  async function signOut() {
    try {
      await endSession();
      navigate('/login', { replace: true });
    } catch (error) {
      setSignOutError(error.message === 'PENDING_OFFLINE_RESPONSES' ? t('pendingBeforeLogout') : t('connectionError'));
    }
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
            {isTeacher || session.courses ? (
              <span>
                {subjectClasses.length > 1 ? (
                  <select aria-label={t('chooseClass')} value={session.classId} onChange={event => {
                    const selected = subjectClasses.find(item => item.id === event.target.value);
                    if (selected) startSession({ ...session, classId: selected.id, className: selected.class_name, subject: selected.subject, topic: selected.topic, studentId: selected.student_id || session.studentId, studentCode: selected.student_code || session.studentCode });
                  }}>
                    {subjectClasses.map(item => <option value={item.id} key={item.id}>{classDisplayName(item.class_name, item.topic)}</option>)}
                  </select>
                ) : <strong>{session?.className || t('classLabel')}</strong>}
                <small>
                  {session?.subject} · {session?.topic}
                </small>
              </span>
            ) : (
              <span>{session?.studentCode}</span>
            )}
          </div>
          {(backendStatus === 'offline' || backendStatus === 'unreachable') && <div
            className={`backend-status backend-${backendStatus}`}
            role="status"
            aria-live="polite"
          >
            <span className="backend-status-dot" aria-hidden="true" />
            {backendStatus === 'offline'
                ? t('offlineLearning')
                : t('backendUnreachable')}
          </div>}
          <div className="topbar-controls">
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
          {signOutError && <p className="form-error" role="alert">{signOutError}</p>}
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
