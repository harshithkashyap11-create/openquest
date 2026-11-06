import { lazy, Suspense, useCallback, useState } from 'react';
import { Plus, BookOpen, Sparkles, Upload, Download, Trash2 } from 'lucide-react';
import api, { getErrorMessage } from '../services/api';
import useAsyncData from '../hooks/useAsyncData';
import { useI18n } from '../i18n/useI18n';
import Button from '../components/ui/Button';
import { LoadingState, ErrorState } from '../components/PageStates';
import { Drawing, AudioPlayback } from '../components/StudioEvidence';
import { questionKinds, newQuestion, downloadFile } from '../services/studioApi';
const QRWorkshop = lazy(() => import('./QRWorkshop'));

export default function TeacherStudio({ activities, reload, root, session }) {
  const { t } = useI18n(); const [tab, setTab] = useState('activities');
  const [draft, setDraft] = useState({ title: '', questions: [], max_attempts: 3 });
  const [saved, setSaved] = useState(null); const [reviewed, setReviewed] = useState(false);
  const [message, setMessage] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function run(fn) { setBusy(true); setError(''); setMessage(''); try { await fn(); } catch(e) { setError(getErrorMessage(e)); } finally { setBusy(false); } }
  function update(next) { setDraft(next); setReviewed(false); }
  function add(questions) {
    setDraft(d => ({ ...d, questions: [...d.questions, ...questions.map(q => { const fields = Object.fromEntries(Object.entries(q).filter(([k]) => !['subject', 'topic', 'provenance'].includes(k))); return { ...fields, id: crypto.randomUUID() }; })] }));
    setReviewed(false); setMessage(t('addedToDraft'));
  }
  async function save() {
    const result = saved && saved.status === 'draft' ? await api.patch(`${root}/activities/${saved.id}`, draft) : await api.post(root + '/activities', draft);
    setSaved(result.data); setMessage(t('draftSaved')); reload();
  }
  async function publish() {
    if (!reviewed) return;
    const result = saved && saved.status === 'draft' ? await api.patch(`${root}/activities/${saved.id}`, draft) : await api.post(root + '/activities', draft);
    const published = (await api.post(`${root}/activities/${result.data.id}/publish`)).data;
    setSaved(published); setMessage(t('activityPublished')); reload();
  }
  return <>
    <nav className="studio-tabs" aria-label={t('studioTools')}>{['activities', 'library', 'qr', 'pathways', 'reports'].map(id => <Button variant="secondary" key={id} aria-pressed={tab === id} onClick={() => { setTab(id); setError(''); }}>{t('studioTab_' + id)}</Button>)}</nav>
    <div className="studio-message" role="status" aria-live="polite">{message}</div>{error && <p role="alert" className="form-error">{error}</p>}
    {tab === 'activities' && <div className="studio-layout"><aside className="studio-sidebar"><Button variant="secondary" onClick={() => { setDraft({ title: '', questions: [], max_attempts: 3 }); setSaved(null); setReviewed(false); setMessage(''); }}><Plus size={16} aria-hidden="true" />{t('newActivity')}</Button>
      {activities.map(a => <button type="button" className="studio-activity-row" aria-pressed={saved?.id === a.id} key={a.id} onClick={() => { setSaved(a); setDraft({ title: a.title, questions: a.questions, max_attempts: a.max_attempts }); setReviewed(false); setMessage(''); }}><strong>{a.title}</strong><small>{a.questions.length} {t('studioQuestions')} · {t(a.status === 'published' ? 'publishedLabel' : 'draftLabel')}</small></button>)}</aside>
      <section className="studio-editor"><label className="studio-field">{t('activityTitle')}<input value={draft.title} maxLength={160} onChange={e => update({ ...draft, title: e.target.value })} /></label>
        <div className="studio-actions"><Button variant="secondary" onClick={() => setTab('library')}><BookOpen size={16} aria-hidden="true" />{t('questionLibrary')}</Button><PDFImport root={root} onImport={add} run={run} /><DraftGenerator root={root} session={session} onGenerate={add} run={run} /></div>
        {saved?.status === 'published' && <p className="studio-note">{t('publishedCopyHelp')}</p>}
        {draft.questions.map((q, i) => <QuestionEditor key={q.id} q={q} index={i} onChange={next => update({ ...draft, questions: draft.questions.map((q, idx) => idx === i ? next : q) })} onSaveLibrary={() => run(async () => { await api.post(root + '/library', q); setMessage(t('savedToLibrary')); })} onRemove={() => update({ ...draft, questions: draft.questions.filter((_, idx) => idx !== i) })} />)}
        {!draft.questions.length && <p className="studio-empty">{t('emptyDraftHelp')}</p>}
        <Button variant="secondary" onClick={() => add([newQuestion()])}><Plus size={16} aria-hidden="true" />{t('addQuestion')}</Button>
        <label className="studio-field">{t('attemptLimit')}<input type="number" min={1} max={10} value={draft.max_attempts} onChange={e => update({ ...draft, max_attempts: Number(e.target.value) })} /></label>
        <label className="studio-review"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />{t('reviewedKeys')}</label>
        <div className="studio-actions"><Button variant="secondary" busy={busy} disabled={!draft.title || !draft.questions.length} onClick={() => run(save)}>{t('saveDraft')}</Button><Button busy={busy} disabled={!reviewed || !draft.title || !draft.questions.length} onClick={() => run(publish)}>{t('publishActivity')}</Button></div>
      </section></div>}
    {tab === 'library' && <QuestionLibrary root={root} onAdd={add} />}
    {tab === 'qr' && <Suspense fallback={<LoadingState />}><QRWorkshop root={root} classId={session.classId} activities={activities} /></Suspense>}
    {tab === 'pathways' && <Pathways root={root} activities={activities} run={run} busy={busy} />}
    {tab === 'reports' && <StudioReports root={root} activities={activities} run={run} />}
  </>;
}

function QuestionEditor({ q, index, onChange, onRemove, onSaveLibrary }) {
  const { t } = useI18n(); const choice = ['choice', 'multiple_select', 'true_false'].includes(q.kind); const mapping = ['matching', 'categorize'].includes(q.kind);
  function change(key, value) { onChange({ ...q, [key]: value }); }
  return <fieldset className="studio-question"><legend>{t('studioQuestion')} {index + 1}</legend><div className="studio-inline-fields"><label className="studio-field">{t('questionFormat')}<select value={q.kind} onChange={e => onChange({ ...newQuestion(e.target.value), id: q.id, text: q.text, standard: q.standard, points: q.points, explanation: q.explanation })}>{questionKinds.map(kind => <option key={kind} value={kind}>{t('kind_' + kind)}</option>)}</select></label><label className="studio-field">{t('pointsLabel')}<input type="number" min={1} max={20} value={q.points || 1} onChange={e => change('points', Number(e.target.value))} /></label></div>
    <label className="studio-field">{t('questionPrompt')}<textarea value={q.text} maxLength={4000} onChange={e => change('text', e.target.value)} /></label>
    {choice && <><p className="studio-muted">{t('selectCorrectKeys')}</p>{q.options.map((option, i) => <div className="studio-option" key={i}><input aria-label={`${t('correctOption')} ${i+1}`} type={q.kind === 'multiple_select' ? 'checkbox' : 'radio'} name={`key-${q.id}`} checked={q.kind === 'multiple_select' ? (q.answer || []).includes(i) : q.answer === i} onChange={() => change('answer', q.kind === 'multiple_select' ? (q.answer || []).includes(i) ? q.answer.filter(n => n !== i) : [...q.answer, i] : i)} /><input type="text" aria-label={`${t('optionLabel')} ${i+1}`} value={option} onChange={e => change('options', q.options.map((o, idx) => idx === i ? e.target.value : o))} /></div>)}</>}
    {mapping && <><label className="studio-field">{t('mapItems')}<textarea value={(q.items || []).join('\n')} onChange={e => change('items', e.target.value.split('\n'))} /></label><label className="studio-field">{t('mapOptions')}<textarea value={q.options.join('\n')} onChange={e => change('options', e.target.value.split('\n'))} /></label>{q.items?.filter(Boolean).map(item => <label className="studio-match-row" key={item}>{item}<select value={q.answer?.[item] || ''} onChange={e => change('answer', { ...q.answer, [item]: e.target.value })}><option value="">{t('chooseAnswer')}</option>{q.options.map(option => <option key={option}>{option}</option>)}</select></label>)}</>}
    {['numeric', 'short_answer'].includes(q.kind) && <label className="studio-field">{t('answerKey')}<input value={q.answer || ''} onChange={e => change('answer', e.target.value)} /></label>}
    {q.kind === 'numeric' && <label className="studio-field">{t('numericTolerance')}<input type="number" min={0} step="any" value={q.tolerance || 0} onChange={e => change('tolerance', Number(e.target.value))} /></label>}
    {q.kind === 'writing' && <p className="studio-note">{t('writingReviewHelp')}</p>}
    <div className="studio-inline-fields"><label className="studio-field">{t('standardLabel')}<input value={q.standard || ''} maxLength={160} onChange={e => change('standard', e.target.value)} /></label><label className="studio-field">{t('hintLabel')}<input value={q.hint || ''} maxLength={2000} onChange={e => change('hint', e.target.value)} /></label></div>
    <label className="studio-field">{t('teacherExplanation')}<textarea value={q.explanation || ''} maxLength={4000} onChange={e => change('explanation', e.target.value)} /></label>
    {choice && <details><summary>{t('distractorSignals')}</summary>{q.options.map((o, i) => <label className="studio-field" key={i}>{o || `${t('optionLabel')} ${i+1}`}<input value={q.distractors?.[String(i)] || ''} onChange={e => change('distractors', { ...q.distractors, [String(i)]: e.target.value })} /></label>)}</details>}
    <div className="studio-actions"><Button variant="secondary" onClick={onSaveLibrary}><BookOpen size={15} aria-hidden="true" />{t('saveToLibrary')}</Button><Button variant="secondary" onClick={onRemove}><Trash2 size={15} aria-hidden="true" />{t('removeQuestion')}</Button></div>
  </fieldset>;
}

function QuestionLibrary({ root, onAdd }) {
  const { t } = useI18n(); const [query, setQuery] = useState('');
  const load = useCallback(async () => (await api.get(root + '/library')).data, [root]); const { data, loading, error, reload } = useAsyncData(load, root);
  if (loading) return <LoadingState />; if (error) return <ErrorState error={error} onRetry={reload} />;
  const rows = data.filter(q => `${q.text} ${q.standard} ${q.explanation} ${JSON.stringify(q.distractors)}`.toLowerCase().includes(query.toLowerCase()));
  return <section><h2>{t('questionLibrary')}</h2><p className="studio-muted">{t('starterBankNote')}</p><label className="studio-field">{t('searchQuestions')}<input value={query} onChange={e => setQuery(e.target.value)} /></label><div className="studio-library">{rows.map(q => <article key={q.id}><span className="studio-tag">{q.standard}</span><h3>{q.text}</h3><ol type="A">{q.options.map((o, i) => <li key={i}>{o}</li>)}</ol><details><summary>{t('answerAndSignals')}</summary><p>{q.options[q.answer]} · {q.explanation}</p>{Object.entries(q.distractors).map(([i, signal]) => <p key={i}>{q.options[i]}: {signal}</p>)}</details><Button variant="secondary" onClick={() => onAdd([q])}><Plus size={16} aria-hidden="true" />{t('addToDraft')}</Button></article>)}</div>{!rows.length && <p>{t('noQuestionsFound')}</p>}</section>;
}

function PDFImport({ root, onImport, run }) {
  const { t } = useI18n(); const [preview, setPreview] = useState(null);
  async function load(e) {
    const file = e.target.files?.[0]; if (!file) return;
    if (file.size > 7_000_000) throw new Error(t('pdfTooLarge'));
    const encoded = await new Promise((resolve, reject) => { const r = new FileReader(); r.onload = () => resolve(r.result.split(',')[1]); r.onerror = reject; r.readAsDataURL(file); });
    setPreview((await api.post(root + '/import-pdf', { filename: file.name, content_base64: encoded }, { timeout: 60000 })).data);
  }
  return <div><label className="button button-secondary"><Upload size={16} aria-hidden="true" />{t('importPDF')}<input type="file" accept="application/pdf,.pdf" className="sr-only" aria-label={t('importPDF')} onChange={e => run(() => load(e))} /></label>{preview && <details open><summary>{t('pdfPreview')}</summary><p>{t('pdfReviewHelp')}</p><pre>{preview.text.slice(0, 1800)}</pre><p>{preview.questions.length} {t('studioQuestions')}</p><Button variant="secondary" disabled={!preview.questions.length} onClick={() => { onImport(preview.questions); setPreview(null); }}>{t('addExtractedDraft')}</Button><Button variant="secondary" onClick={() => setPreview(null)}>{t('cancel')}</Button></details>}</div>;
}

function DraftGenerator({ root, session, onGenerate, run }) {
  const { t } = useI18n(); const [open, setOpen] = useState(false); const [kind, setKind] = useState('choice'); const [difficulty, setDifficulty] = useState('standard'); const [count, setCount] = useState(3); const [preview, setPreview] = useState(null);
  return <div><Button variant="secondary" onClick={() => setOpen(!open)}><Sparkles size={16} aria-hidden="true" />{t('generateDraft')}</Button>{open && <div><label className="studio-field">{t('questionFormat')}<select value={kind} onChange={e => setKind(e.target.value)}>{['choice', 'numeric', 'short_answer', 'writing'].map(k => <option key={k} value={k}>{t('kind_' + k)}</option>)}</select></label><label className="studio-field">{t('difficultyLabel')}<select value={difficulty} onChange={e => setDifficulty(e.target.value)}>{['easier', 'standard', 'harder'].map(k => <option key={k} value={k}>{t('difficulty_' + k)}</option>)}</select></label><label className="studio-field">{t('questionCount')}<input type="number" min={1} max={10} value={count} onChange={e => setCount(Number(e.target.value))} /></label><Button variant="secondary" onClick={() => run(async () => setPreview((await api.post(root + '/generate', { topic: session.topic, count, kind, difficulty }, { timeout: 60000 })).data))}>{t('createSuggestion')}</Button>{preview && <><p className="studio-tag">{preview.provider}</p><p>{t('generatedReviewHelp')}</p>{preview.questions.map(q => <p key={q.id}>{q.text}</p>)}<Button onClick={() => { onGenerate(preview.questions); setPreview(null); setOpen(false); }}>{t('acceptDraftItems')}</Button><Button variant="secondary" onClick={() => setPreview(null)}>{t('rejectSuggestion')}</Button></>}</div>}</div>;
}

function Pathways({ root, activities, run, busy }) {
  const { t } = useI18n(); const [title, setTitle] = useState(''); const [ids, setIds] = useState([]); const [threshold, setThreshold] = useState(0);
  const load = useCallback(async () => (await api.get(root + '/sets')).data, [root]); const { data, loading, error, reload } = useAsyncData(load, root);
  const published = activities.filter(a => a.status === 'published');
  return <section className="studio-editor"><h2>{t('activityPathways')}</h2><p>{t('pathwayHelp')}</p><label className="studio-field">{t('pathwayTitle')}<input value={title} onChange={e => setTitle(e.target.value)} /></label>{published.map(a => <label className="studio-review" key={a.id}><input type="checkbox" checked={ids.includes(a.id)} onChange={e => setIds(e.target.checked ? [...ids, a.id] : ids.filter(id => id !== a.id))} />{ids.includes(a.id) ? `${ids.indexOf(a.id)+1}. ` : ''}{a.title}</label>)}<p>{t('selectionDefinesOrder')}</p><label className="studio-field">{t('unlockPercent')}<input type="number" min={0} max={100} value={threshold} onChange={e => setThreshold(Number(e.target.value))} /></label><Button busy={busy} disabled={!title || !ids.length} onClick={() => run(async () => { await api.post(root + '/sets', { title, activity_ids: ids, minimum_percent: threshold }); setIds([]); setTitle(''); reload(); })}>{t('savePathway')}</Button>{loading && <LoadingState />}{error && <ErrorState error={error} onRetry={reload} />}{data?.map(s => <div className="studio-path" key={s.id}><h3>{s.title}</h3><ol>{s.activity_ids.map(id => <li key={id}>{activities.find(a => a.id === id)?.title}</li>)}</ol><small>{s.minimum_percent}% · {t('unlockRequirement')}</small></div>)}</section>;
}

function StudioReports({ root, activities, run }) {
  const { t } = useI18n(); const load = useCallback(async () => { const [report, integration] = await Promise.all([api.get(root + '/report'), api.get(root + '/integrations')]); return { ...report.data, integration: integration.data }; }, [root]); const { data, loading, error, reload } = useAsyncData(load, root);
  if (loading) return <LoadingState />; if (error) return <ErrorState error={error} onRetry={reload} />;
  return <section><div className="studio-actions"><h2>{t('standardsAndWork')}</h2><Button variant="secondary" onClick={reload}>{t('refresh')}</Button><Button variant="secondary" onClick={() => run(() => downloadFile(root + '/grades.csv', 'classpulse-grades.csv'))}><Download size={16} aria-hidden="true" />{t('exportGradeCSV')}</Button></div><p className="studio-muted">{t('gradeExportScope')}</p><div className="studio-summary"><p><strong>{data.submitted_students}/{data.total_students}</strong>{t('studentsSubmitted')}</p><p><strong>{data.work.length}</strong>{t('savedAttempts')}</p></div><p>{t('standardsReportScope')}</p>
    <div className="studio-table-wrap"><table className="studio-table"><thead><tr>{['standardLabel', 'pointsLabel', 'responseCount', 'pendingReview'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead><tbody>{data.standards.map(s => <tr key={s.standard}><td>{s.standard}</td><td>{s.earned}/{s.possible}</td><td>{s.responses}</td><td>{s.pending}</td></tr>)}</tbody></table></div>
    <p className="studio-note">{t('lmsIntegration')}: {t(data.integration.token_configured && data.integration.mapped_activities && data.integration.mapped_students ? 'lmsConfigured' : 'lmsNotConfigured')} · {t('lmsAutomatic')}: {t(data.integration.automatic ? 'lmsEnabled' : 'lmsDisabled')}</p>
    {data.work.map(w => <WorkReview key={w.id} w={w} activity={activities.find(a => a.id === w.activity_id)} root={root} run={run} reload={reload} />)}{!data.work.length && <p className="studio-empty">{t('noWorkYet')}</p>}
  </section>;
}

function WorkReview({ w, activity, root, run, reload }) {
  const { t } = useI18n();
  const [delivery, setDelivery] = useState('');
  return <article className="studio-work"><h3>{w.title}</h3><p>{w.student_code} · {t('attemptLabel')} {w.attempt} · {w.score}/{w.possible} · {w.pending_review} {t('pendingReview')}</p><div className="studio-actions"><Button variant="secondary" onClick={() => run(() => downloadFile(`${root}/work/${w.id}/export.pdf`, 'student-work.pdf'))}>{t('downloadWorkPDF')}</Button><Button variant="secondary" disabled={w.pending_review > 0} onClick={() => run(async () => { const r = (await api.post(`${root}/work/${w.id}/passback`)).data; setDelivery(r.status); reload(); })}>{t('sendGradeToLMS')}</Button><small>{delivery || w.lms_status}</small></div><details><summary>{t('reviewStudentWork')}</summary>{activity?.questions.map(q => <section key={q.id} className="studio-question"><h4>{q.text}</h4><p>{t('answerLabel')}: {typeof w.answers[q.id] === 'object' ? JSON.stringify(w.answers[q.id]) : ['choice', 'true_false'].includes(q.kind) ? q.options[w.answers[q.id]] : String(w.answers[q.id] ?? '')}</p><p>{w.reasoning[q.id]}</p>{w.media[q.id]?.strokes?.length > 0 && <Drawing strokes={w.media[q.id].strokes} />}<AudioPlayback media={w.media[q.id]} /><p>{w.media[q.id]?.transcript}</p>{w.results[q.id].signal && <p className="studio-note">{w.results[q.id].signal} · {t('choiceSignalScope')}</p>}<form className="studio-actions" onSubmit={e => { e.preventDefault(); const form = new FormData(e.currentTarget); run(async () => { await api.patch(`${root}/work/${w.id}/grade`, { question_id: q.id, points: Number(form.get('points')), comment: form.get('comment') }); reload(); }); }}><label className="studio-field">{t('pointsLabel')}<input type="number" name="points" min={0} max={q.points || 1} defaultValue={w.results[q.id].earned ?? 0} required /></label><label className="studio-field">{t('teacherComment')}<input name="comment" maxLength={4000} defaultValue={w.results[q.id].comment || ''} /></label><Button type="submit" variant="secondary">{t('saveReview')}</Button></form>{(w.conversations[q.id] || []).map((m, i) => <p key={i}>{m.role}: {m.content}</p>)}</section>)}</details></article>;
}
