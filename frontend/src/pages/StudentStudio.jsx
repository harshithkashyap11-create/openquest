import { useRef, useState } from 'react';
import { ArrowLeft, LockKeyhole, Download } from 'lucide-react';
import api, { getErrorMessage } from '../services/api';
import { useI18n } from '../i18n/useI18n';
import Button from '../components/ui/Button';
import StudioEvidence, { Drawing, AudioPlayback } from '../components/StudioEvidence';
import { downloadFile } from '../services/studioApi';

export default function StudentStudio({ activities, reload, root }) {
  const { t } = useI18n(); const [selected, setSelected] = useState(null);
  const activity = activities.find(a => a.id === selected);
  if (activity && !activity.locked) return <ActivityResponse key={activity.id} activity={activity} root={root} reload={reload} onBack={() => setSelected(null)} />;
  return <section><div className="studio-library">{activities.map(a => <article key={a.id}><span className="studio-tag">{a.questions.length} {t('studioQuestions')}</span><h2>{a.title}</h2><p>{a.attempts.length}/{a.max_attempts} {t('savedAttempts')}</p>{a.locked && <p className="studio-muted"><LockKeyhole size={15} aria-hidden="true" /> {a.locked}</p>}<Button variant="secondary" disabled={Boolean(a.locked)} aria-label={`${t('startActivity')} ${a.title}`} onClick={() => setSelected(a.id)}>{a.attempts.length ? t('viewOrRetry') : t('startActivity')}</Button></article>)}</div>{!activities.length && <p className="studio-empty">{t('noActivitiesYet')}</p>}</section>;
}

function ActivityResponse({ activity, root, reload, onBack }) {
  const { t } = useI18n(); const [answers, setAnswers] = useState({}); const [reasoning, setReasoning] = useState({}); const [media, setMedia] = useState({});
  const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false); const request = useRef(null);
  const [recordingQuestions, setRecordingQuestions] = useState({});
  const attempts = activity.attempts || [];
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const payload = { answers, reasoning: Object.fromEntries(activity.questions.map(q => [q.id, reasoning[q.id] || media[q.id]?.transcript || ''])), media };
      const fingerprint = JSON.stringify(payload);
      if (request.current?.fingerprint !== fingerprint) request.current = { fingerprint, request_id: crypto.randomUUID() };
      const work = (await api.post(`${root}/activities/${activity.id}/submit`, { ...payload, request_id: request.current.request_id }, { timeout: 60000 })).data;
      setMessage(`${t('savedAttempt')} ${work.attempt}`); request.current = null; await reload();
    } catch(e) { setError(getErrorMessage(e)); }
    finally { setBusy(false); }
  }
  return <section><Button variant="secondary" onClick={onBack}><ArrowLeft size={16} aria-hidden="true" />{t('backToActivities')}</Button><h2>{activity.title}</h2><div role="status" className="studio-message">{message}</div>{error && <p role="alert" className="form-error">{error}</p>}
    {attempts.slice().reverse().map(w => <SavedWork key={w.id} w={w} activity={activity} root={root} />)}
    {attempts.length < activity.max_attempts ? <form className="studio-editor" onSubmit={submit}><p className="studio-muted">{t('attemptLabel')} {attempts.length+1}/{activity.max_attempts}</p>{activity.questions.map((q, i) => <fieldset className="studio-question" key={q.id}><legend>{t('studioQuestion')} {i+1} · {q.points || 1} {t('pointsLabel')}</legend><h3>{q.text}</h3>{q.standard && <span className="studio-tag">{q.standard}</span>}<AnswerControl q={q} value={answers[q.id]} onChange={answer => setAnswers(a => ({ ...a, [q.id]: answer }))} />{q.hint && <details><summary>{t('hintLabel')}</summary><p>{q.hint}</p></details>}
      <label className="studio-field">{t('explainReasoning')}<textarea value={reasoning[q.id] || ''} maxLength={10000} onChange={e => setReasoning(r => ({ ...r, [q.id]: e.target.value }))} /></label><StudioEvidence value={media[q.id]} onChange={value => setMedia(m => ({ ...m, [q.id]: value }))} onRecordingChange={recording => setRecordingQuestions(r => r[q.id] === recording ? r : { ...r, [q.id]: recording })} />
    </fieldset>)}<Button type="submit" busy={busy} disabled={Object.values(recordingQuestions).some(Boolean)}>{t('submitActivity')}</Button></form> : <p className="studio-note">{t('allAttemptsUsed')}</p>}
  </section>;
}

function AnswerControl({ q, value, onChange }) {
  const { t } = useI18n();
  if (['choice', 'true_false', 'multiple_select'].includes(q.kind)) return <div className="studio-answer-list">{q.options.map((o, i) => <label key={i}><input type={q.kind === 'multiple_select' ? 'checkbox' : 'radio'} name={`answer-${q.id}`} required={q.kind !== 'multiple_select'} checked={q.kind === 'multiple_select' ? (value || []).includes(i) : value === i} onChange={() => onChange(q.kind === 'multiple_select' ? (value || []).includes(i) ? value.filter(n => n !== i) : [...(value || []), i] : i)} /><span>{o}</span></label>)}</div>;
  if (['matching', 'categorize'].includes(q.kind)) return <div>{q.items.map(item => <label className="studio-match-row" key={item}>{item}<select required value={value?.[item] || ''} onChange={e => onChange({ ...value, [item]: e.target.value })}><option value="">{t('chooseAnswer')}</option>{q.options.map(option => <option key={option}>{option}</option>)}</select></label>)}</div>;
  return <label className="studio-field">{t('yourAnswer')}{q.kind === 'writing' ? <textarea required maxLength={10000} value={value || ''} onChange={e => onChange(e.target.value)} /> : <input required maxLength={2000} inputMode={q.kind === 'numeric' ? 'decimal' : undefined} value={value || ''} onChange={e => onChange(e.target.value)} />}</label>;
}

function SavedWork({ w, activity, root }) {
  const { t } = useI18n(); const [error, setError] = useState('');
  return <article className="studio-work"><h3>{t('attemptLabel')} {w.attempt} · {w.score}/{w.possible}</h3>{w.pending_review > 0 && <p>{w.pending_review} {t('pendingReview')}</p>}<Button variant="secondary" onClick={async () => { try { await downloadFile(`${root}/work/${w.id}/export.pdf`, 'my-work.pdf'); } catch(e) { setError(getErrorMessage(e)); } }}><Download size={16} aria-hidden="true" />{t('downloadWorkPDF')}</Button>{error && <p role="alert">{error}</p>}
    {activity.questions.map(q => <section className="studio-question" key={q.id}><h4>{q.text}</h4><p>{t('answerLabel')}: {['choice', 'true_false'].includes(q.kind) ? q.options[w.answers[q.id]] : typeof w.answers[q.id] === 'object' ? JSON.stringify(w.answers[q.id]) : String(w.answers[q.id] || '')}</p><p>{w.reasoning[q.id]}</p>{w.media[q.id]?.strokes?.length > 0 && <Drawing strokes={w.media[q.id].strokes} />}<AudioPlayback media={w.media[q.id]} /><p>{w.media[q.id]?.transcript}</p><p>{w.results[q.id].explanation}</p>{w.results[q.id].comment && <p>{t('teacherComment')}: {w.results[q.id].comment}</p>}<FeedbackBox root={root} work={w} question={q} /></section>)}
  </article>;
}

function FeedbackBox({ root, work, question }) {
  const { t, language } = useI18n(); const [text, setText] = useState(''); const [messages, setMessages] = useState(work.conversations[question.id] || []); const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try { const data = (await api.post(`${root}/work/${work.id}/feedback`, { question_id: question.id, message: text, language }, { timeout: 60000 })).data; setMessages(data.messages); setText(''); }
    catch(e) { setError(getErrorMessage(e)); } finally { setBusy(false); }
  }
  return <div><div className="studio-chat">{messages.map((m, i) => <div key={i}>{m.provider && <span className="studio-tag">{m.provider}</span>}<p className={m.role}>{m.content}</p></div>)}</div>{messages.length < 10 && <form onSubmit={submit}><label className="studio-field">{t('messageToTutor')}<textarea required maxLength={2000} value={text} onChange={e => setText(e.target.value)} /></label><Button type="submit" variant="secondary" busy={busy}>{t('getFeedback')}</Button></form>}{error && <p className="form-error" role="alert">{error}</p>}</div>;
}
