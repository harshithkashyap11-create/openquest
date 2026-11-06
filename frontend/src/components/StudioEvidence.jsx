import { useEffect, useRef, useState } from 'react';
import { Mic, Square, Undo2, Trash2 } from 'lucide-react';
import Button from './ui/Button';
import { useI18n } from '../i18n/useI18n';

export function Drawing({ strokes = [], onChange }) {
  const { t } = useI18n(); const canvas = useRef(null); const drawing = useRef(false); const current = useRef(strokes);
  useEffect(() => { current.current = strokes; }, [strokes]);
  useEffect(() => {
    const c = canvas.current; const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, c.width, c.height); ctx.strokeStyle = '#164e47'; ctx.lineWidth = 3; ctx.lineCap = 'round';
    for (const stroke of strokes) {
      ctx.beginPath(); stroke.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.stroke();
    }
  }, [strokes]);
  function point(e) { const r = canvas.current.getBoundingClientRect(); return [(e.clientX - r.left) * 800 / r.width, (e.clientY - r.top) * 320 / r.height]; }
  return <div className="studio-drawing"><canvas width="800" height="320" ref={canvas} aria-label={t('drawingBoard')} role="img" style={{ touchAction: onChange ? 'none' : 'auto' }}
    onPointerDown={onChange ? e => { drawing.current = true; e.currentTarget.setPointerCapture(e.pointerId); const next = [...current.current, [point(e)]]; current.current = next; onChange(next); } : undefined}
    onPointerMove={onChange ? e => { if (!drawing.current) return; const rows = current.current; const next = [...rows.slice(0, -1), [...rows.at(-1), point(e)]]; current.current = next; onChange(next); } : undefined}
    onPointerUp={() => { drawing.current = false; }} onPointerCancel={() => { drawing.current = false; }} />
    {onChange && <div className="studio-actions"><Button variant="secondary" onClick={() => onChange(strokes.slice(0, -1))}><Undo2 size={15} aria-hidden="true" />{t('undoStroke')}</Button><Button variant="secondary" onClick={() => onChange([])}><Trash2 size={15} aria-hidden="true" />{t('clearDrawing')}</Button><small>{t('drawingAlternative')}</small></div>}
  </div>;
}

export function AudioPlayback({ media }) {
  if (!media?.audio) return null;
  return <audio controls preload="none" src={`data:${media.mime};base64,${media.audio}`} />;
}

export default function StudioEvidence({ value = {}, onChange, onRecordingChange }) {
  const { t, language } = useI18n(); const [recording, setRecording] = useState(false); const [error, setError] = useState('');
  const recorder = useRef(null); const stream = useRef(null); const recognition = useRef(null); const timer = useRef(null); const latest = useRef(value);
  const changed = useRef(onChange);
  useEffect(() => { latest.current = value; changed.current = onChange; }, [value, onChange]);
  useEffect(() => { onRecordingChange?.(recording); }, [recording, onRecordingChange]);
  useEffect(() => () => { clearTimeout(timer.current); recognition.current?.stop(); if (recorder.current?.state === 'recording') { recorder.current.onstop = null; recorder.current.stop(); } stream.current?.getTracks().forEach(track => track.stop()); }, []);
  async function record() {
    setError('');
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) throw new Error(t('recordingUnavailable'));
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = ['audio/webm', 'audio/ogg', 'audio/mp4'].find(type => MediaRecorder.isTypeSupported(type));
      const r = new MediaRecorder(stream.current, mime ? { mimeType: mime } : undefined); recorder.current = r; const chunks = [];
      r.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
      r.onstop = async () => {
        clearTimeout(timer.current); recognition.current?.stop(); stream.current?.getTracks().forEach(track => track.stop());
        const blob = new Blob(chunks, { type: r.mimeType });
        if (blob.size > 2_500_000) { setError(t('recordingTooLarge')); setRecording(false); return; }
        const reader = new FileReader(); reader.onload = () => { changed.current({ ...latest.current, audio: reader.result.split(',')[1], mime: r.mimeType.split(';')[0] }); setRecording(false); }; reader.onerror = () => { setRecording(false); setError(t('recordingUnavailable')); }; reader.readAsDataURL(blob);
      };
      r.start(); setRecording(true); timer.current = setTimeout(() => { if (r.state === 'recording') r.stop(); }, 60000);
      const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (Recognition) {
        const speech = new Recognition(); recognition.current = speech; speech.continuous = true; speech.lang = { en: 'en-US', hi: 'hi-IN', te: 'te-IN' }[language];
        speech.onresult = e => { const text = Array.from(e.results).map(item => item[0].transcript).join(' '); changed.current({ ...latest.current, transcript: text }); };
        speech.onerror = () => setError(t('transcriptUnavailable')); speech.start();
      }
    } catch (e) { stream.current?.getTracks().forEach(track => track.stop()); setError(e.message || t('recordingUnavailable')); }
  }
  return <details className="studio-evidence" open><summary>{t('showThinking')}</summary><Drawing strokes={value.strokes || []} onChange={strokes => onChange({ ...value, strokes })} />
    <div className="studio-actions"><Button variant="secondary" onClick={recording ? () => recorder.current?.stop() : record}>{recording ? <Square size={16} aria-hidden="true" /> : <Mic size={16} aria-hidden="true" />}{t(recording ? 'stopRecording' : 'recordVoice')}</Button>{value.audio && <Button variant="secondary" onClick={() => onChange({ ...value, audio: undefined, mime: undefined })}>{t('removeRecording')}</Button>}<small>{t('recordingLimit')}</small></div>
    <AudioPlayback media={value} />
    <label className="studio-field">{t('editableTranscript')}<textarea value={value.transcript || ''} onChange={e => onChange({ ...value, transcript: e.target.value })} maxLength={10000} /></label>
    <small className="studio-muted">{t('mediaFeedbackScope')}</small>{error && <p role="alert" className="form-error">{error}</p>}
  </details>;
}
