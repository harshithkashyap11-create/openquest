import { lazy, Suspense } from 'react';
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
} from 'react-router-dom';
import EffectsProvider from './context/EffectsProvider';
const AppShell = lazy(() => import('./components/AppShell'));
import { LoadingState } from './components/PageStates';
import { DemoSessionProvider } from './context/DemoSessionContext';
import { useDemoSession } from './context/useDemoSession';
import { I18nProvider } from './i18n/I18nProvider';
import './App.css';

const LearningEvidence = lazy(() => import('./pages/LearningEvidence'));
const LessonStudio = lazy(() => import('./pages/LessonStudio'));
const LearningLab = lazy(() => import('./pages/LearningLab'));
const TeacherQuizzes = lazy(() => import('./pages/TeacherQuizzes'));
const StudentQuizzes = lazy(() => import('./pages/StudentQuizzes'));
const Assessment = lazy(() => import('./pages/Assessment'));
const ClassInsights = lazy(() => import('./pages/ClassInsights'));
const Intervention = lazy(() => import('./pages/Intervention'));
const Login = lazy(() => import('./pages/Login'));
const NotFound = lazy(() => import('./pages/NotFound'));
const StudentDashboard = lazy(() => import('./pages/StudentDashboard'));
const StudentProgress = lazy(() => import('./pages/StudentProgress'));
const ClassProgress = lazy(() => import('./pages/ClassProgress'));
const TeacherDashboard = lazy(() => import('./pages/TeacherDashboard'));

function RoleRoute({ role }) {
  const { session } = useDemoSession();
  if (!session) return <Navigate to="/login" replace />;
  if (role && session.role !== role) {
    return (
      <Navigate
        to={
          session.role === 'teacher'
            ? '/teacher/overview'
            : '/student/dashboard'
        }
        replace
        state={{ notice: role }}
      />
    );
  }
  return <Outlet />;
}

function AppRoutes() {
  return (
    <Suspense fallback={<LoadingState />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<RoleRoute role="teacher" />}>
          <Route path="/teacher" element={<AppShell role="teacher" />}>
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="overview" element={<TeacherDashboard />} />
            <Route path="learning" element={<LearningEvidence />} />
            <Route path="lessons" element={<LessonStudio />} />
            <Route path="quizzes" element={<TeacherQuizzes />} />
            <Route path="insights" element={<ClassInsights />} />
            <Route path="interventions" element={<Intervention />} />
            <Route path="progress" element={<ClassProgress />} />
          </Route>
        </Route>
        <Route element={<RoleRoute role="student" />}>
          <Route path="/student" element={<AppShell role="student" />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<StudentDashboard />} />
            <Route path="learning" element={<LearningLab />} />
            <Route path="quizzes" element={<StudentQuizzes />} />
            <Route path="quizzes/:quizId" element={<StudentQuizzes />} />
            <Route path="assessment" element={<Assessment />} />
            <Route path="interventions" element={<Intervention />} />
            <Route
              path="interventions/:assignmentId"
              element={<Intervention />}
            />
            <Route path="progress" element={<StudentProgress />} />
          </Route>
        </Route>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <I18nProvider>
      <EffectsProvider>
        <DemoSessionProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </DemoSessionProvider>
      </EffectsProvider>
    </I18nProvider>
  );
}
