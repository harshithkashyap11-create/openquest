import { useCallback, useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import jsQR from 'jsqr';
import { Camera, Square, Printer } from 'lucide-react';
import api, { getErrorMessage } from '../services/api';
import useAsyncData from '../hooks/useAsyncData';
import { useI18n } from '../i18n/useI18n';
import Button from '../components/ui/Button';
import { ErrorState, LoadingState } from '../components/PageStates';
import { scannedCard } from '../services/qrCards';

export default function QRWorkshop({ root, classId, activities }) {
  const { t } = useI18n(); const [activityId, setActivityId] = useState(''); const [questionId, setQuestionId] = useState('');
  const [active, setActive] = useState(null); const [showCards, setShowCards] = useState(false); const [cards, setCards] = useState([]); const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [scanning, setScanning] = useState(false);
  const video = useRef(null); const stream = useRef(null); const running = useRef(false); const frame = useRef(null); const seen = useRef(new Map());
  const current = useRef(active);
  useEffect(() => { current.current = active; }, [active]);
  const load = useCallback(async () => { const [roster, sessions] = await Promise.all([api.get(root + '/roster'), api.get(root + '/qr-sessions')]); return { roster: roster.data, sessions: sessions.data }; }, [root]);
  const { data, loading, error: loadError, reload } = useAsyncData(load, root);
  const activity = activities.find(a => a.id === activityId); const questions = activity?.questions.filter(q => ['choice', 'true_false'].includes(q.kind) && q.options.length <= 4) || [];
  function stop() { running.current = false; cancelAnimationFrame(frame.current); stream.current?.getTracks().forEach(track => track.stop()); stream.current = null; setScanning(false); }
  useEffect(() => () => { running.current = false; cancelAnimationFrame(frame.current); stream.current?.getTracks().forEach(track => track.stop()); }, []);
  async function run(fn) { setBusy(true); setError(''); try { await fn(); } catch(e) { setError(e.response ? getErrorMessage(e) : e.message); } finally { setBusy(false); } }
  async function response(studentId, option) {
    const session = current.current;
    if (!session || session.status !== 'open') return;
    const result = (await api.post(`${root}/qr-sessions/${session.id}/responses`, { student_id: studentId, option })).data;
    if (current.current?.id === result.id) setActive(result);
  }
  async function startCamera() {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error(t('cameraUnavailable'));
    stream.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1280 } }, audio: false });
    if (!video.current) { stream.current.getTracks().forEach(track => track.stop()); return; }
    video.current.srcObject = stream.current; await video.current.play(); running.current = true; setScanning(true); seen.current.clear();
    const canvas = document.createElement('canvas'); const ctx = canvas.getContext('2d', { willReadFrequently: true }); let last = 0;
    async function scan(now) {
      if (!running.current) return;
      if (video.current?.readyState >= 2 && now - last > 500) {
        last = now; canvas.width = video.current.videoWidth; canvas.height = video.current.videoHeight; ctx.drawImage(video.current, 0, 0);
        for (let i = 0; i < 12; i++) {
          const image = ctx.getImageData(0, 0, canvas.width, canvas.height); const code = jsQR(image.data, image.width, image.height);
          if (!code) break;
          const card = scannedCard(code, classId);
          if (card && data.roster.some(s => s.student_id === card.student_id) && card.option < (current.current?.counts.length || 0) && seen.current.get(card.student_id) !== card.option) {
            try { await response(card.student_id, card.option); seen.current.set(card.student_id, card.option); } catch(e) { setError(getErrorMessage(e)); stop(); return; }
          }
          const points = Object.values(code.location).filter(p => p && typeof p.x === 'number'); const xs = points.map(p => p.x), ys = points.map(p => p.y);
          const x = Math.max(0, Math.min(...xs)-8), y = Math.max(0, Math.min(...ys)-8);
          ctx.fillStyle = '#fff'; ctx.fillRect(x, y, Math.max(...xs)-x+8, Math.max(...ys)-y+8);
        }
      }
      if (running.current) frame.current = requestAnimationFrame(scan);
    }
    frame.current = requestAnimationFrame(scan);
  }
  async function prepareCards() {
    const images = await Promise.all(data.roster.map(async s => ({ ...s, image: await QRCode.toDataURL(JSON.stringify({ app: 'classpulse', class_id: classId, student_id: s.student_id }), { width: 280, margin: 1, errorCorrectionLevel: 'M' }) })));
    setCards(images); setShowCards(true);
  }
  if (loading) return <LoadingState />; if (loadError) return <ErrorState error={loadError} onRetry={reload} />;
  return <section><h2>{t('qrResponseRoom')}</h2><p>{t('qrWorkflowHelp')}</p>{error && <p className="form-error" role="alert">{error}</p>}
    <div className="studio-actions"><Button variant="secondary" busy={busy} onClick={() => run(prepareCards)}><Printer size={16} aria-hidden="true" />{t('prepareResponseCards')}</Button>{showCards && <><Button variant="secondary" onClick={() => window.print()}>{t('printCards')}</Button><Button variant="secondary" onClick={() => setShowCards(false)}>{t('hideCards')}</Button></>}</div>
    {showCards && <div className="studio-qr-cards">{cards.map(s => <article className="studio-qr-card" key={s.student_id}><strong>{s.student_code}</strong><div className="studio-qr-grid"><b className="top">A</b><b className="right">B</b><b className="bottom">C</b><b className="left">D</b><img alt={`${t('responseCard')} ${s.student_code}`} src={s.image} /></div><small>{t('cardOrientationHelp')}</small></article>)}</div>}
    <div className="studio-editor"><label className="studio-field">{t('chooseActivity')}<select value={activityId} onChange={e => { setActivityId(e.target.value); setQuestionId(''); }}><option value="">{t('chooseActivity')}</option>{activities.filter(a => a.status === 'published').map(a => <option value={a.id} key={a.id}>{a.title}</option>)}</select></label><label className="studio-field">{t('studioQuestion')}<select value={questionId} onChange={e => setQuestionId(e.target.value)}><option value="">{t('chooseQuestion')}</option>{questions.map(q => <option value={q.id} key={q.id}>{q.text}</option>)}</select></label><Button busy={busy} disabled={!questionId} onClick={() => run(async () => { stop(); setActive((await api.post(root + '/qr-sessions', { activity_id: activityId, question_id: questionId })).data); reload(); })}>{t('openResponseSession')}</Button></div>
    {data.sessions.length > 0 && <label className="studio-field">{t('resumeResponseSession')}<select value={active?.id || ''} onChange={e => { stop(); setActive(data.sessions.find(s => s.id === e.target.value) || null); }}><option value="">{t('chooseSession')}</option>{data.sessions.map(s => <option key={s.id} value={s.id}>{s.question.text} · {s.status} · {s.responded}</option>)}</select></label>}
    {active && <section className="studio-work"><h3>{active.question.text}</h3><p>{active.responded}/{data.roster.length} {t('responseCount')} · {active.status}</p><div className="studio-summary">{active.question.options.map((o, i) => <p key={i}><strong>{active.counts[i]}</strong>{'ABCD'[i]}. {o}</p>)}</div>
      <video className="studio-qr-video" ref={video} playsInline muted aria-label={t('cameraPreview')} />
      <div className="studio-actions"><Button variant="secondary" disabled={active.status !== 'open'} busy={busy} onClick={() => scanning ? stop() : run(startCamera)}>{scanning ? <Square size={16} aria-hidden="true" /> : <Camera size={16} aria-hidden="true" />}{t(scanning ? 'stopScanning' : 'scanResponseCards')}</Button><Button variant="secondary" disabled={active.status !== 'open'} onClick={() => run(async () => { stop(); setActive((await api.post(`${root}/qr-sessions/${active.id}/close`)).data); reload(); })}>{t('closeResponseSession')}</Button></div>
      <details><summary>{t('manualResponseEntry')}</summary><p>{t('manualResponseHelp')}</p><div className="studio-table-wrap"><table className="studio-table"><thead><tr><th>{t('student')}</th><th>{t('answerLabel')}</th></tr></thead><tbody>{data.roster.map(s => <tr key={s.student_id}><td>{s.student_code}</td><td><select aria-label={`${t('answerLabel')} ${s.student_code}`} disabled={active.status !== 'open' || busy} value={active.responses[s.student_id] ?? ''} onChange={e => run(() => response(s.student_id, Number(e.target.value)))}><option value="" disabled>—</option>{active.question.options.map((_, i) => <option value={i} key={i}>{'ABCD'[i]}</option>)}</select></td></tr>)}</tbody></table></div></details>
    </section>}
  </section>;
}
