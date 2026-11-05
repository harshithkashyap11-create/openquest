import { useCallback, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { LoadingState, ErrorState } from '../components/PageStates';
import { LessonReader } from '../components/LearningParts';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { listLessons, generateLesson, editLesson, reviewLesson } from '../services/learningApi';
import { getCopilotTaxonomy } from '../services/classpulseApi';
import api, { getErrorMessage } from '../services/api';
import './Learning.css';

export default function LessonStudio() {
  const { session } = useDemoSession();
  const { t, language } = useI18n();
  const [search] = useSearchParams();
  const load = useCallback(() => Promise.all([listLessons(session.classId), getCopilotTaxonomy()]), [session.classId]);
  const { data, loading, error, reload } = useAsyncData(load, session.classId);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [keysReviewed, setKeysReviewed] = useState(false);
  const [languageReviewed, setLanguageReviewed] = useState(false);
  async function action(fn) {
    setBusy(true); setMessage('');
    try { const result = await fn(); setSelected(result); setKeysReviewed(false); setLanguageReviewed(false); await reload(); }
    catch (e) { setMessage(getErrorMessage(e)); }
    finally { setBusy(false); }
  }
  async function generate(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = { misconception_code: form.get('code'), language: form.get('language'), allow_fallback: form.get('fallback') === 'on', difficulty: form.get('difficulty'), duration_minutes: Number(form.get('duration')) };
    const storageKey = `classpulse.lesson-command:${session.classId}`;
    let prior;
    try { prior = JSON.parse(sessionStorage.getItem(storageKey)); } catch {}
    const requestId = prior?.signature === JSON.stringify(payload) ? prior.requestId : crypto.randomUUID();
    sessionStorage.setItem(storageKey, JSON.stringify({ signature: JSON.stringify(payload), requestId }));
    await action(async () => {
      const result = await generateLesson(session.classId, { ...payload, request_id: requestId });
      sessionStorage.removeItem(storageKey); return result;
    });
  }
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const [lessons, taxonomy] = data;
  const codes = (taxonomy[session.subject]?.find(x => x.topic === session.topic)?.misconceptions || []).filter(c => !['M06', 'FOLLOWUP'].includes(c.code));
  const current = selected?.class_id === session.classId ? selected : null;
  return <div className="page-content learning-page">
    <PageHeader title={t('lessonStudio')} description={t('studioDescription')} />
    <section className="panel"><p>{session.subject} · {session.topic} · {session.className}</p>
      <form className="learning-form" onSubmit={generate}>
        <label htmlFor="lesson-code">{t('misconception')}</label><select id="lesson-code" name="code" defaultValue={search.get('code') || codes[0]?.code} required>{codes.map(c => <option key={c.code} value={c.code}>{c.code} · {c.category}</option>)}</select>
        <label htmlFor="lesson-language">{t('teachingLanguage')}</label><select id="lesson-language" name="language" defaultValue={language}><option value="en">English</option><option value="hi">हिन्दी</option><option value="te">తెలుగు</option></select>
        <label htmlFor="lesson-difficulty">{t('recommendedLevel')}</label><select id="lesson-difficulty" name="difficulty"><option value="foundation">{t('foundationLevel')}</option><option value="standard">{t('standardLevel')}</option><option value="challenging">{t('challengeLevel')}</option></select>
        <label htmlFor="lesson-duration">{t('durationMinutes')}</label><input id="lesson-duration" name="duration" type="number" min={5} max={60} defaultValue={15} required aria-describedby="lesson-duration-help" />
        <p className="field-help" id="lesson-duration-help">{t('durationHelp')}</p>
        <label className="learning-check"><input name="fallback" type="checkbox" />{t('allowTemplateFallback')}</label>
        <button className="button button-primary" disabled={busy}>{busy ? t('loading') : t('generateLessonDraft')}</button>
      </form>
    </section>
    {message && <p className="form-error" role="alert">{message}</p>}
    {lessons.length > 0 && <section className="panel"><h2>{t('savedLessons')}</h2><div className="learning-actions">{lessons.map(item => <button className="button button-secondary" key={item.id} onClick={() => { setSelected(item); setKeysReviewed(false); setLanguageReviewed(false); }}>
      {item.revision.content.title} · {item.revision.language} · {item.revision.status}</button>)}</div></section>}
    {current && <section className="panel"><LessonReader lesson={current} />
      <div className="learning-form">
        {current.revision.status === 'draft' && <>
          <label className="learning-check"><input type="checkbox" checked={keysReviewed} onChange={e => setKeysReviewed(e.target.checked)} />{t('reviewedAnswerKeys')}</label>
          <label className="learning-check"><input type="checkbox" checked={languageReviewed} onChange={e => setLanguageReviewed(e.target.checked)} />{t('reviewedLanguage')}</label>
          <button className="button button-primary" disabled={busy || !keysReviewed || !languageReviewed} onClick={() => action(() => reviewLesson(current.id, { revision_id: current.revision.id, action: 'approve', answer_keys_reviewed: true, language_reviewed: true }))}>{t('approveRevision')}</button>
          <button className="button button-secondary" disabled={busy} onClick={() => action(() => reviewLesson(current.id, { revision_id: current.revision.id, action: 'reject' }))}>{t('rejectDraft')}</button>
        </>}
        {current.revision.status === 'approved' && <button className="button button-primary" disabled={busy} onClick={() => action(() => reviewLesson(current.id, { revision_id: current.revision.id, action: 'publish' }))}>{t('publishLesson')}</button>}
        {current.revision.status === 'published' && <button className="button button-primary" disabled={busy} onClick={async () => { setBusy(true); try { const r = (await api.post(`/lessons/${current.id}/assign`, { revision_id: current.revision.id })).data; setMessage(t('linkedActivities', { count: r.assignments_linked })); } catch(e) { setMessage(getErrorMessage(e)); } finally { setBusy(false); } }}>{t('attachApprovedActivities')}</button>}
        {current.revision.status === 'published' && <button className="button button-secondary" disabled={busy} onClick={() => action(() => reviewLesson(current.id, { revision_id: current.revision.id, action: 'archive' }))}>{t('archiveLesson')}</button>}
      </div>
      <details><summary>{t('editLesson')}</summary><LessonEditor key={current.revision.id} lesson={current} busy={busy} onSave={content => action(() => editLesson(current.id, { revision_id: current.revision.id, content }))} /></details>
    </section>}
  </div>;
}

function LessonEditor({ lesson, busy, onSave }) {
  const { t } = useI18n();
  const [content, setContent] = useState(() => structuredClone(lesson.revision.content));
  const change = (key, value) => setContent(c => ({ ...c, [key]: value }));
  return <form className="learning-form" onSubmit={e => { e.preventDefault(); onSave(content); }}>
    <label htmlFor="edit-title">{t('lessonTitle')}</label><input id="edit-title" required value={content.title} onChange={e => change('title', e.target.value)} />
    <label htmlFor="edit-objectives">{t('objectives')}</label><textarea id="edit-objectives" required value={content.objectives.join('\n')} onChange={e => change('objectives', e.target.value.split('\n'))} />
    <label htmlFor="edit-explanation">{t('explanation')}</label><textarea id="edit-explanation" rows={6} required value={content.explanation} onChange={e => change('explanation', e.target.value)} />
    <label htmlFor="edit-correction">{t('misconceptionCorrection')}</label><textarea id="edit-correction" required value={content.misconception_correction} onChange={e => change('misconception_correction', e.target.value)} />
    <label htmlFor="edit-example">{t('workedExample')}</label><input id="edit-example" required value={content.worked_example.problem} onChange={e => change('worked_example', { ...content.worked_example, problem: e.target.value })} />
    <label htmlFor="edit-steps">{t('reasoningSteps')}</label><textarea id="edit-steps" required value={content.worked_example.steps.join('\n')} onChange={e => change('worked_example', { ...content.worked_example, steps: e.target.value.split('\n') })} />
    {content.practice_questions.map((q, i) => <fieldset key={i}><legend>{t('question')} {i + 1}</legend>
      <label htmlFor={`edit-q-${i}`}>{t('question')}</label><input id={`edit-q-${i}`} required value={q.prompt} onChange={e => change('practice_questions', content.practice_questions.map((x, n) => n === i ? { ...x, prompt: e.target.value } : x))} />
      <label htmlFor={`edit-a-${i}`}>{t('answerKey')}</label><input id={`edit-a-${i}`} required value={q.answer} onChange={e => change('practice_questions', content.practice_questions.map((x, n) => n === i ? { ...x, answer: e.target.value } : x))} />
    </fieldset>)}
    <button className="button button-primary" disabled={busy}>{t('saveNewRevision')}</button>
  </form>;
}
