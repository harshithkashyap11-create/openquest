import { useRef, useState } from 'react';
import { useI18n } from '../i18n/useI18n';
import { corrections, correctDiagnosis } from '../services/learningApi';

// Both teacher surfaces use the existing versioned, idempotent correction API.
export default function DiagnosisReview({ diagnosisId, originalCode, codes, onSaved }) {
  const { t } = useI18n();
  const [code, setCode] = useState(originalCode);
  const [reason, setReason] = useState('');
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [failed, setFailed] = useState(false);
  const command = useRef(null);
  async function save() {
    setBusy(true); setMessage(''); setFailed(false);
    try {
      const history = await corrections(diagnosisId);
      const latest = history.at(-1);
      const storageKey = `classpulse.correction-command:${diagnosisId}`;
      let prior;
      try { prior = JSON.parse(sessionStorage.getItem(storageKey)); } catch {}
      if (!command.current) {
        command.current = prior?.code === code && prior?.reason === reason ? prior : {
          code, reason, expected_version: latest?.version || 0, request_id: crypto.randomUUID(),
        };
      }
      sessionStorage.setItem(storageKey, JSON.stringify(command.current));
      await correctDiagnosis(diagnosisId, command.current);
      sessionStorage.removeItem(storageKey);
      command.current = null;
      await onSaved();
      setConfirm(false); setMessage(t('mapDecisionSaved'));
    } catch {
      // Keep the same command identity: retry reconciles a lost response through
      // the server receipt before it considers the correction version.
      setFailed(true); setMessage(t('mapSaveUnknown'));
    } finally { setBusy(false); }
  }
  return <form className="learning-form" onSubmit={event => { event.preventDefault(); setMessage(''); setConfirm(true); }}>
    <h3>{t('teacherCorrection')}</h3>
    <p>{t('mapOriginalSuggestion')}: <strong>{originalCode}</strong></p>
    <label htmlFor={`decision-${diagnosisId}`}>{t('mapTeacherDecision')}</label>
    <select id={`decision-${diagnosisId}`} value={code} disabled={busy || confirm} onChange={e => { setCode(e.target.value); command.current = null; }}>
      {[...new Set(['CORRECT', ...codes.map(c => c.code), 'FOLLOW_UP'])].map(c => <option key={c} value={c}>{c}</option>)}
    </select>
    <label htmlFor={`reason-${diagnosisId}`}>{t('reviewReason')}</label>
    <textarea id={`reason-${diagnosisId}`} minLength={5} maxLength={1000} required value={reason} disabled={busy || confirm} onChange={e => { setReason(e.target.value); command.current = null; }} />
    {confirm ? <div>
      <p>{t('mapConfirmDecision', { code })}</p>
      <div className="learning-actions">
        <button type="button" className="button button-primary" disabled={busy} onClick={save}>{busy ? t('loadingShort') : t('mapConfirmSave')}</button>
        <button type="button" className="button button-secondary" disabled={busy} onClick={() => { setConfirm(false); setMessage(''); }}>{t('cancel')}</button>
      </div>
    </div> : <button className="button button-primary" disabled={busy}>{t('mapReviewCorrection')}</button>}
    {message && <p role={failed ? 'alert' : 'status'}>{message}</p>}
  </form>;
}
