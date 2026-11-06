import { useCallback, useEffect, useState } from 'react';
import PageHeader from '../components/PageHeader';
import { useDemoSession } from '../context/useDemoSession';
import api, { getErrorMessage } from '../services/api';
import './Learning.css';
import './InclusiveLearning.css';

export default function InclusiveLearning() {
  const { session } = useDemoSession();
  return session.role === 'teacher' ? <Teacher classId={session.classId} /> : <Student studentId={session.studentId} />;
}

function Teacher({ classId }) {
  const base = `/classes/${classId}/inclusive`;
  const [catalog, setCatalog] = useState({ supports: [], presets: [] });
  const [sources, setSources] = useState([]); const [lessons, setLessons] = useState([]);
  const [adaptations, setAdaptations] = useState([]); const [audience, setAudience] = useState({ students: [], groups: [] });
  const [sourceId, setSourceId] = useState(''); const [lessonId, setLessonId] = useState('');
  const [supports, setSupports] = useState([]); const [selected, setSelected] = useState(null);
  const [blocks, setBlocks] = useState([]); const [questions, setQuestions] = useState([]);
  const [students, setStudents] = useState([]); const [groups, setGroups] = useState([]); const [wholeClass, setWholeClass] = useState(false);
  const [note, setNote] = useState(''); const [busy, setBusy] = useState(false); const [message, setMessage] = useState('');
  const refresh = useCallback(async () => {
    const [c, s, a, l, people] = await Promise.all([api.get(`${base}/supports`), api.get(`${base}/sources`), api.get(`${base}/adaptations`), api.get(`/classes/${classId}/lessons`), api.get(`${base}/audience`)]);
    setCatalog(c.data); setSources(s.data); setAdaptations(a.data); setLessons(l.data); setAudience(people.data);
  }, [base, classId]);
  useEffect(() => { refresh().catch(e => setMessage(getErrorMessage(e))); }, [refresh]);
  function choose(item) {
    if (!item) { setSelected(null); setBlocks([]); setQuestions([]); setNote(''); return; }
    setSelected(item); setNote(item.review_note || ''); setQuestions(item.draft.questions || []);
    setBlocks((item.analysis?._adapted_blocks?.blocks || []).map(b => ({ block_id: b.block_id, content: b.content })));
  }
  async function run(fn, success) {
    setBusy(true); setMessage('');
    try { const result = await fn(); if (result?.draft) choose(result); await refresh(); if (success) setMessage(success); }
    catch (error) { setMessage(getErrorMessage(error)); } finally { setBusy(false); }
  }
  async function importFile(event) {
    const file = event.target.files?.[0]; if (!file) return;
    await run(async () => {
      const buffer = await file.arrayBuffer(); const bytes = new Uint8Array(buffer); let binary = '';
      for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      const result = await api.post(`${base}/sources`, { filename: file.name, content_base64: btoa(binary) }); setSourceId(result.data.id);
    }, 'Lesson imported. Review the extracted source before adapting.');
    event.target.value = '';
  }
  function toggle(value, values, setter) { setter(values.includes(value) ? values.filter(x => x !== value) : [...values, value]); }
  async function download(format) {
    await run(async () => {
      const result = await api.get(`${base}/adaptations/${selected.id}/export/${format}`, { responseType: 'blob' });
      const url = URL.createObjectURL(result.data); const link = document.createElement('a'); link.href = url; link.download = `inclusive-lesson.${format === 'report' ? 'json' : format}`; link.click(); URL.revokeObjectURL(url);
    });
  }
  const source = sources.find(x => x.id === sourceId);
  const savedBlocks = (selected?.analysis?._adapted_blocks?.blocks || []).map(b => ({ block_id: b.block_id, content: b.content }));
  const hasUnsavedEdits = !!selected && (JSON.stringify(blocks) !== JSON.stringify(savedBlocks) || JSON.stringify(questions) !== JSON.stringify(selected.draft.questions || []));
  return <div className="page-content learning-page inclusive-page">
    <PageHeader title="Inclusive Learning" description="Adapt lessons around the supports a learner chooses with their teacher." />
    {message && <p role="status" className="panel">{message}</p>}
    <section className="panel"><h2>1. Choose a lesson</h2>
      <label htmlFor="inclusive-file">Import a lesson (PDF, DOCX, TXT or Markdown)</label><input id="inclusive-file" type="file" accept=".pdf,.docx,.txt,.md" disabled={busy} onChange={importFile} />
      <div className="inclusive-row"><label htmlFor="existing-lesson">Or use a ClassPulse lesson</label><select id="existing-lesson" value={lessonId} onChange={e => setLessonId(e.target.value)}><option value="">Choose a lesson</option>{lessons.filter(l => l.revision?.language === 'en').map(l => <option key={l.id} value={l.id}>{l.revision.content.title}</option>)}</select>
        <button type="button" className="button button-secondary" disabled={!lessonId || busy} onClick={() => run(async () => { const r = await api.post(`${base}/sources/from-lesson`, { lesson_id: lessonId }); setSourceId(r.data.id); }, 'Lesson added.')}>Use lesson</button></div>
      <label htmlFor="inclusive-source">Saved sources</label><select id="inclusive-source" value={sourceId} onChange={e => setSourceId(e.target.value)}><option value="">Choose a source</option>{sources.map(s => <option key={s.id} value={s.id}>{s.source.title}</option>)}</select>
      {source && <details><summary>Review extracted source</summary>{source.source.parsing_warnings.map(w => <p key={w}>{w}</p>)}{source.source.blocks.map(b => <p key={b.block_id}><strong>{b.block_id}</strong> {b.text}</p>)}</details>}
    </section>
    <section className="panel"><h2>2. Select supports</h2><p>Choose supports for the individual learner. A diagnosis is not required.</p>
      <div className="inclusive-row">{catalog.presets.map(p => <button type="button" className="button button-secondary" key={p.id} onClick={() => setSupports(p.support_ids)}>{p.name}</button>)}</div>
      <fieldset><legend>Support options</legend>{catalog.supports.map(s => <label className="inclusive-option" key={s.id}><input type="checkbox" checked={supports.includes(s.id)} onChange={() => toggle(s.id, supports, setSupports)} /><span><strong>{s.title}</strong><br />{s.description}</span></label>)}</fieldset>
      <button className="button button-primary" disabled={busy || !sourceId || !supports.length} onClick={() => run(async () => (await api.post(`${base}/adaptations`, { source_id: sourceId, support_ids: supports }, { timeout: 180000 })).data, 'Draft ready for review.')}>{busy ? 'Working…' : 'Create adaptation'}</button>
      <p>Generation requires a configured AI provider. Source text is sent to that provider.</p>
    </section>
    <section className="panel"><h2>3. Review adaptations</h2><label htmlFor="inclusive-draft">Saved adaptations</label><select id="inclusive-draft" value={selected?.id || ''} onChange={e => choose(adaptations.find(a => a.id === e.target.value) || null)}><option value="">Choose a draft</option>{adaptations.map(a => <option key={a.id} value={a.id}>{a.draft.title} · version {a.version}</option>)}</select></section>
    {selected && <>
      <section className="panel"><h2>{selected.draft.title}</h2><p>Version {selected.version} · {selected.approved_version === selected.version ? 'Approved' : 'Draft — not approved'}</p>
        <div className="inclusive-compare"><div><h3>Original</h3>{(sources.find(s => s.id === selected.source_id)?.source.blocks || []).map(b => <p key={b.block_id}><strong>{b.block_id}</strong> {b.text}</p>)}</div>
          <div><h3>Adapted blocks</h3>{blocks.map((b, i) => <label key={b.block_id} className="inclusive-block">{b.block_id}<textarea rows={4} value={b.content} onChange={e => setBlocks(blocks.map((x, n) => n === i ? { ...x, content: e.target.value } : x))} /></label>)}</div></div>
        <h3>Practice questions</h3><p>Review the answer key and hints before approval.</p>
        {questions.map((q, i) => <fieldset key={i}><legend>Question {i + 1}</legend>{['prompt', 'answer'].map(key => <label className="inclusive-block" key={key}>{key === 'prompt' ? 'Question' : 'Answer key'}<input value={q[key]} onChange={e => setQuestions(questions.map((x, n) => n === i ? { ...x, [key]: e.target.value } : x))} /></label>)}<button type="button" className="button button-secondary" onClick={() => setQuestions(questions.filter((_, n) => n !== i))}>Remove question</button></fieldset>)}
        <button className="button button-secondary" onClick={() => setQuestions([...questions, { prompt: '', answer: '', hints: [] }])}>Add question</button>{' '}
        <button className="button button-secondary" disabled={busy || !blocks.length} onClick={() => run(async () => (await api.patch(`${base}/adaptations/${selected.id}`, { version: selected.version, blocks, questions })).data, 'Saved. Run verification again before approval.')}>Save edits</button>{' '}
        <button className="button button-secondary" disabled={busy || selected.findings.length > 0} onClick={() => run(async () => (await api.post(`${base}/adaptations/${selected.id}/verify`, { version: selected.version, review_note: 'Verification requested' }, { timeout: 180000 })).data, 'Verification complete. Review the findings.')}>Run verification</button>
        {hasUnsavedEdits && <p role="status">Save your edits and verify the new version before approval or assignment.</p>}
        <h3>Verification findings</h3>{selected.findings.length ? selected.findings.map((f, i) => <p key={i}><strong>{f.status}</strong> · {f.check_id || f.source_ref} · {f.explanation || f.message}{f.evidence && <> — “{f.evidence}”</>}</p>) : <p>Current version needs verification.</p>}
        <p>Automated checks can miss issues. Review source coverage, safety, support suitability, and practice answers.</p>
        <label className="inclusive-block" htmlFor="review-note">Review decision and acknowledgement</label><textarea id="review-note" value={note} onChange={e => setNote(e.target.value)} rows={3} />
        <button className="button button-primary" disabled={busy || hasUnsavedEdits || !selected.findings.length || note.trim().length < 10} onClick={() => run(async () => (await api.post(`${base}/adaptations/${selected.id}/approve`, { version: selected.version, review_note: note })).data, 'Version approved.')}>Approve current version</button>
        <h3>Downloads</h3><div className="inclusive-row">{['html', 'pdf', 'txt', 'ssml', 'report'].map(f => <button className="button button-secondary" key={f} onClick={() => download(f)} disabled={busy}>{f === 'report' ? 'Teacher report' : f.toUpperCase()}</button>)}</div>
      </section>
      <section className="panel"><h2>4. Assign approved lesson</h2><label className="inclusive-option"><input type="checkbox" checked={wholeClass} onChange={e => setWholeClass(e.target.checked)} />Whole class</label>
        <fieldset><legend>Individual students</legend>{audience.students.map(s => <label className="inclusive-option" key={s.id}><input type="checkbox" checked={students.includes(s.id)} onChange={() => toggle(s.id, students, setStudents)} />{s.name}</label>)}</fieldset>
        {audience.groups.length > 0 && <fieldset><legend>Groups</legend>{audience.groups.map(g => <label className="inclusive-option" key={g.id}><input type="checkbox" checked={groups.includes(g.id)} onChange={() => toggle(g.id, groups, setGroups)} />{g.name}</label>)}</fieldset>}
        <button className="button button-primary" disabled={busy || hasUnsavedEdits || selected.approved_version !== selected.version || !(wholeClass || students.length || groups.length)} onClick={() => run(() => api.post(`${base}/adaptations/${selected.id}/assign`, { student_ids: students, group_ids: groups, whole_class: wholeClass }), 'Lesson assigned.')}>Assign lesson</button>
      </section>
    </>}
  </div>;
}

function Student({ studentId }) {
  const [lessons, setLessons] = useState([]); const [size, setSize] = useState(20); const [spacing, setSpacing] = useState(1.7);
  const [message, setMessage] = useState(''); const [answers, setAnswers] = useState({}); const [results, setResults] = useState({});
  const base = `/students/${studentId}/inclusive/lessons`;
  useEffect(() => { api.get(base).then(r => setLessons(r.data)).catch(e => setMessage(getErrorMessage(e))); }, [base]);
  useEffect(() => () => { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); }, []);
  async function submit(item) {
    try { const r = await api.post(`${base}/${item.id}/practice`, { answers: item.content.questions.map((_, i) => answers[`${item.id}-${i}`] || '') }); setResults({ ...results, [item.id]: r.data.results }); setMessage('Your practice has been saved.'); }
    catch (e) { setMessage(getErrorMessage(e)); }
  }
  return <div className="page-content learning-page inclusive-page"><PageHeader title="Inclusive Learning" description="Your lessons, with reading controls that work for you." />
    {message && <p role="status" className="panel">{message}</p>}
    <section className="panel inclusive-row"><label htmlFor="reader-size">Text size: {size}px</label><input id="reader-size" type="range" min="16" max="32" value={size} onChange={e => setSize(Number(e.target.value))} />
      <label htmlFor="reader-spacing">Line spacing: {spacing}</label><input id="reader-spacing" type="range" min="1.4" max="2.4" step="0.1" value={spacing} onChange={e => setSpacing(Number(e.target.value))} /></section>
    {!lessons.length && <p className="panel">No lessons have been assigned yet.</p>}
    {lessons.map(item => <section className="panel" key={item.id}><article style={{ fontSize: size, lineHeight: spacing }}><h2>{item.content.title}</h2>{item.content.objectives.length > 0 && <><h3>What you will learn</h3><ul>{item.content.objectives.map((o, i) => <li key={i}>{o}</li>)}</ul></>}{item.content.blocks?.length ? item.content.blocks.map((b, i) => b.type === 'heading' ? <h3 key={i}>{b.content}</h3> : <p key={i}>{b.content}</p>) : item.content.text.split('\n\n').map((p, i) => <p key={i}>{p}</p>)}</article>
      {'speechSynthesis' in window && <div className="inclusive-row"><button className="button button-secondary" onClick={() => { window.speechSynthesis.cancel(); window.speechSynthesis.speak(new SpeechSynthesisUtterance(`${item.content.title}. ${item.content.text}`)); }}>Read aloud</button><button className="button button-secondary" onClick={() => window.speechSynthesis.cancel()}>Stop reading</button></div>}
      {item.content.questions.length > 0 && <form onSubmit={e => { e.preventDefault(); submit(item); }}><h3>Practice</h3>{item.content.questions.map((q, i) => <div key={i}><label className="inclusive-block" htmlFor={`answer-${item.id}-${i}`}>{q.prompt}</label><input id={`answer-${item.id}-${i}`} required value={answers[`${item.id}-${i}`] || ''} onChange={e => setAnswers({ ...answers, [`${item.id}-${i}`]: e.target.value })} />{q.hints?.length > 0 && <details><summary>Show a hint</summary>{q.hints.map((h, n) => <p key={n}>{h}</p>)}</details>}{(results[item.id] || item.progress?.results)?.[i] && <p role="status">{(results[item.id] || item.progress.results)[i].correct ? 'That matches the answer.' : 'Try again or ask your teacher for help.'}</p>}</div>)}<button className="button button-primary">Check practice</button></form>}
    </section>)}
  </div>;
}
