import { useCallback, useEffect, useState } from 'react';
import PageHeader from '../components/PageHeader';
import { LoadingState, ErrorState } from '../components/PageStates';
import { EvidenceState, LessonReader } from '../components/LearningParts';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { learnerState, studentLessons, tutorHistory, requestHint } from '../services/learningApi';
import { getStudentInterventions } from '../services/classpulseApi';
import { getErrorMessage } from '../services/api';
import { savePackage, offlinePackages, queuedCommands, queuePractice, synchronize } from '../services/offlineLearning';
import './Learning.css';

export default function LearningLab() {
  const { session } = useDemoSession();
  const { t } = useI18n();
  const [online, setOnline] = useState(navigator.onLine);
  const [queue, setQueue] = useState([]);
  const [downloaded, setDownloaded] = useState([]);
  const [message, setMessage] = useState('');
  const load = useCallback(async () => {
    const saved = await offlinePackages(session.studentId);
    setDownloaded(saved.map(p => p.key));
    try {
      const [states, lessons, assignments] = await Promise.all([learnerState(session.studentId), studentLessons(session.studentId), getStudentInterventions(session.studentId)]);
      return { states, lessons, assignments, cached: false };
    } catch (error) {
      if (!saved.length) throw error;
      return { states: [], lessons: saved.filter(p => p.kind === 'lesson').map(p => p.item), assignments: saved.filter(p => p.kind === 'activity').map(p => p.item), cached: true };
    }
  }, [session.studentId]);
  const { data, loading, error, reload } = useAsyncData(load, session.studentId);
  const refreshQueue = useCallback(async () => setQueue(await queuedCommands(session.studentId)), [session.studentId]);
  const sync = useCallback(async () => { await synchronize(session.studentId, true); await refreshQueue(); }, [session.studentId, refreshQueue]);
  useEffect(() => {
    let active = true;
    queuedCommands(session.studentId).then(q => { if (active) setQueue(q); }).catch(() => {});
    const connect = () => { setOnline(true); void sync().catch(() => {}); };
    const disconnect = () => setOnline(false);
    window.addEventListener('online', connect); window.addEventListener('offline', disconnect);
    return () => { active = false; window.removeEventListener('online', connect); window.removeEventListener('offline', disconnect); };
  }, [session.studentId, sync]);
  async function download(kind, item) {
    try {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();
        if (!registration) throw new Error(t('offlineBuildRequired'));
        await navigator.serviceWorker.ready;
        await new Promise((resolve, reject) => {
          const channel = new MessageChannel();
          const timeout = setTimeout(() => reject(new Error(t('localStorageUnavailable'))), 15000);
          channel.port1.onmessage = event => { clearTimeout(timeout); channel.port1.close(); if (event.data.ready) resolve(); else reject(new Error(t('localStorageUnavailable'))); };
          registration.active.postMessage({ type: 'CACHE_LEARNING_SHELL', urls: performance.getEntriesByType('resource').map(r => r.name) }, [channel.port2]);
        });
      }
      const saved = await savePackage(session.studentId, kind, item);
      setDownloaded(d => [...d, saved.key]); setMessage(t('downloadedForDevice'));
    } catch (e) { setMessage(e.response ? getErrorMessage(e) : e.message || t('localStorageUnavailable')); }
  }
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return <div className="page-content learning-page">
    <PageHeader title={t('learningLab')} description={t('labDescription')} />
    <section className="panel" aria-live="polite"><strong>{online ? t('onlineLearning') : t('offlineLearning')}</strong>
      {data.cached && <p>{t('cachedContentNotice')}</p>}<p>{t('offlineInferenceNotice')}</p>
      <p>{t('pendingSync', { count: queue.filter(q => q.status !== 'synchronized').length })}</p>
      <button className="button button-secondary" disabled={!online} onClick={() => sync().catch(e => setMessage(e.message))}>{t('syncResponses')}</button>
      {queue.map(q => <p key={q.key}>{t('practiceResponse')} · {t(`queue_${q.status}`)}{q.status === 'conflict' && ` · ${t('syncConflict')}`}</p>)}
    </section>
    {message && <p role="status" className="panel">{message}</p>}
    {data.states.map(s => <EvidenceState key={`${s.subject}:${s.topic}`} state={s} />)}
    <h2>{t('approvedActivities')}</h2>
    {data.assignments.filter(a => a.status !== 'completed').map(assignment => <section className="panel" key={assignment.id}>
      <h3>{assignment.intervention.title}</h3><p>{assignment.intervention.explanation}</p>
      <button className="button button-secondary" disabled={!online} onClick={() => download('activity', assignment)}>{downloaded.includes(`${session.studentId}:activity:${assignment.id}`) ? t('downloadedForDevice') : t('downloadActivity')}</button>
      <TutorActivity assignment={assignment} online={online} onQueue={async answers => {
        await queuePractice(session.studentId, assignment, answers); await refreshQueue();
        if (online) await sync();
      }} />
    </section>)}
    <h2>{t('publishedLessons')}</h2>
    {data.lessons.map(lesson => <section className="panel" key={lesson.id}><LessonReader lesson={lesson} />
      <button className="button button-secondary" disabled={!online} onClick={() => download('lesson', lesson)}>{downloaded.includes(`${session.studentId}:lesson:${lesson.id}`) ? t('downloadedForDevice') : t('downloadLesson')}</button>
    </section>)}
    {!data.lessons.length && <p className="panel">{t('noPublishedLessons')}</p>}
  </div>;
}

function TutorActivity({ assignment, online, onQueue }) {
  const { t, language } = useI18n();
  const [index, setIndex] = useState(0);
  const [response, setResponse] = useState('');
  const [answers, setAnswers] = useState({});
  const [events, setEvents] = useState([]);
  const [linkedLessons, setLinkedLessons] = useState([]);
  const [liveHints, setLiveHints] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  useEffect(() => {
    if (!online) return;
    let active = true;
    tutorHistory(assignment.id).then(h => { if (active) { setEvents(h.events); setLinkedLessons(h.lessons || []); } }).catch(() => {});
    return () => { active = false; };
  }, [assignment.id, online]);
  async function hint() {
    setBusy(true); setMessage('');
    try {
      const payload = { question_index: index, language, response, generation_mode: liveHints ? 'live' : 'template' };
      const storageKey = `classpulse.hint-command:${assignment.id}`;
      let prior; try { prior = JSON.parse(sessionStorage.getItem(storageKey)); } catch {}
      const signature = JSON.stringify(payload);
      const requestId = prior?.signature === signature ? prior.requestId : crypto.randomUUID();
      sessionStorage.setItem(storageKey, JSON.stringify({ signature, requestId }));
      const data = await requestHint(assignment.id, { ...payload, request_id: requestId });
      sessionStorage.removeItem(storageKey);
      setEvents(e => [...e, data]); setResponse('');
    } catch (e) { setMessage(getErrorMessage(e)); }
    finally { setBusy(false); }
  }
  const shown = events.filter(e => e.question_index === index);
  return <div className="learning-form">
    {linkedLessons.filter(l => l.revision.language === language).map(l => <LessonReader key={l.revision.id} lesson={l} />)}
    <label htmlFor={`tutor-question-${assignment.id}`}>{t('practiceQuestions')}</label>
    <select id={`tutor-question-${assignment.id}`} value={index} onChange={e => { setIndex(Number(e.target.value)); setResponse(''); }}>{assignment.intervention.practice_questions.map((q, i) => <option key={i} value={i}>{q.question}</option>)}</select>
    <ol className="hint-ladder" aria-live="polite">{shown.map(h => <li key={h.level} lang={h.language}><strong>{t('hintLevel', { level: h.level })}</strong><p>{h.hint}</p><small>{h.provider} · {h.model || t('noLiveInference')}</small>{h.feedback && <p>{t('provisionalFeedback')}: {h.feedback.replaceAll('_', ' ')}</p>}</li>)}</ol>
    <label htmlFor={`tutor-response-${assignment.id}`}>{t('describeYourStep')}</label><textarea id={`tutor-response-${assignment.id}`} value={response} onChange={e => setResponse(e.target.value)} maxLength={1500} />
    <label className="learning-check"><input type="checkbox" checked={liveHints} onChange={e => setLiveHints(e.target.checked)} />{t('useLiveTutor')}</label>
    <button className="button button-secondary" disabled={!online || busy || shown.length >= 4 || (shown.length > 0 && !response.trim())} onClick={hint}>{t('nextHint')}</button>
    {!online && <p>{t('hintsNeedConnection')}</p>}
    <form className="learning-form" onSubmit={async e => { e.preventDefault(); setBusy(true); try { await onQueue(Object.entries(answers).map(([i, answer]) => ({ question_index: Number(i), answer }))); setMessage(t('responseSavedLocally')); } catch (error) { setMessage(error.message); } finally { setBusy(false); } }}>
      {assignment.intervention.practice_questions.map((q, i) => <div className="learning-form" key={i}>
        <label htmlFor={`offline-answer-${assignment.id}-${i}`}>{q.question}</label>
        <input id={`offline-answer-${assignment.id}-${i}`} maxLength={200} value={answers[i] || ''} onChange={e => setAnswers(a => ({ ...a, [i]: e.target.value }))} required />
      </div>)}
      <button className="button button-primary" disabled={busy}>{t('savePracticeResponses')}</button>
    </form>
    {message && <p role="status">{message}</p>}
  </div>;
}
