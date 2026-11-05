import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState, RefreshNotice } from '../components/PageStates';
import Drawer from '../components/ui/Drawer';
import DiagnosisReview from '../components/DiagnosisReview';
import { useDemoSession } from '../context/useDemoSession';
import { useI18n } from '../i18n/useI18n';
import useAsyncData from '../hooks/useAsyncData';
import { misconceptionMap, mapEvidence } from '../services/learningApi';
import { getCopilotTaxonomy } from '../services/classpulseApi';
import './MisconceptionMap.css';
import './Learning.css';

export default function MisconceptionMap() {
  const { session } = useDemoSession();
  // Remount all selection and mutation state when the class context changes.
  return <MapWorkspace key={session.classId} session={session} />;
}

function MapWorkspace({ session }) {
  const { t, language } = useI18n();
  const load = useCallback(() => misconceptionMap(session.classId), [session.classId]);
  const { data, loading, error, refreshing, reload } = useAsyncData(load, session.classId);
  const [selection, setSelection] = useState(null);
  const formatDate = value => value ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' }).format(new Date(value)) : t('notAvailable');
  if (!session.classId) return <EmptyState title={t('mapSelectClass')} />;
  if (loading) return <LoadingState />;
  if (error && !data) return <ErrorState message={t('mapLoadFailed')} error={error} onRetry={reload} />;
  const choose = value => setSelection(value);
  return <div className="page-content map-page">
    <PageHeader title={t('mapTitle')} description={t('mapDescription')} context={session.className}
      actions={<button className="button button-secondary" disabled={refreshing} onClick={reload}>{t('refresh')}</button>} />
    <p className="map-context">{data.subject} · {data.topic}</p>
    <RefreshNotice error={error} refreshing={refreshing} onRetry={reload} />
    <section className="panel map-attention" aria-labelledby="attention-title">
      <h2 id="attention-title">{t('mapAttention')}</h2>
      <p>{t('mapAttentionRule')}</p>
      <div className="attention-links">
        <Link to="/teacher/overview"><strong>{data.attention.pending_diagnoses}</strong>{t('mapPendingDiagnosis')}</Link>
        <button onClick={() => choose({ review_only: true })}><strong>{data.attention.pending_reviews}</strong>{t('mapPendingReviews')}</button>
        <button onClick={() => choose({ uncertain_only: true })}><strong>{data.attention.uncertain}</strong>{t('mapUncertain')}</button>
        <Link to="/teacher/interventions#groups"><strong>{data.attention.proposed_groups}</strong>{t('mapProposedGroups')}</Link>
        <Link to="/teacher/interventions#assignments"><strong>{data.attention.ready_for_reassessment}</strong>{t('mapReady')}</Link>
      </div>
    </section>
    <section className="panel" aria-labelledby="map-concepts-title">
      <h2 id="map-concepts-title">{t('mapConcepts')}</h2>
      <p>{t('mapCounts', { count: data.total_responses, students: data.total_students })}</p>
      <p className="muted-note">{t('mapPeriod', { from: formatDate(data.period_from), to: formatDate(data.period_to) })}</p>
      <p className="muted-note">{t('mapRules')}</p>
      {data.concepts.length ? <ul className="concept-map" aria-label={t('mapConcepts')}>
        {data.concepts.map(concept => <li key={concept.code}>
          <button type="button" aria-pressed={selection?.code === concept.code} onClick={() => choose({ code: concept.code })}>
            <span><strong>{concept.code}</strong> · {t(`mapConcept_${concept.code}`)}</span>
            <span className="map-count">{t('mapConceptCounts', { count: concept.response_count, total: data.total_responses, students: concept.student_count })}</span>
            <span className="map-bar" aria-hidden="true"><span style={{ width: `${concept.response_count / Math.max(data.total_responses, 1) * 100}%` }} /></span>
            <span>{t('mapReviewCounts', { pending: concept.pending_reviews, uncertain: concept.uncertain, reviewed: concept.reviewed })}</span>
            {concept.response_count === 1 && <small>{t('mapLimitedEvidence')}</small>}
          </button>
        </li>)}
      </ul> : <EmptyState title={t('mapEmpty')}><Link to="/teacher/overview">{t('mapCreateEvidence')}</Link></EmptyState>}
      <p className="muted-note" role="status">{t('mapRefreshed', { time: formatDate(data.queried_at) })}</p>
    </section>
    {selection && <ConceptEvidence key={JSON.stringify(selection)} classId={session.classId} selection={selection} session={session} onSaved={reload} />}
    <Link className="button button-secondary" to="/teacher/guide">{t('mapGuide')}</Link>
  </div>;
}

function ConceptEvidence({ classId, selection, session, onSaved }) {
  const { t, language } = useI18n();
  const [offset, setOffset] = useState(0);
  const load = useCallback(() => mapEvidence(classId, { ...selection, limit: 20, offset }), [classId, selection, offset]);
  const { data, loading, error, reload } = useAsyncData(load, `${classId}:${JSON.stringify(selection)}:${offset}`);
  const [selectedId, setSelectedId] = useState(null);
  const [reviewedItem, setReviewedItem] = useState(null);
  const taxonomyLoad = useCallback(() => getCopilotTaxonomy(), []);
  const taxonomy = useAsyncData(taxonomyLoad, 'taxonomy');
  const codes = taxonomy.data?.[session.subject]?.find(x => x.topic === session.topic)?.misconceptions || [];
  const selected = selectedId ? (reviewedItem || data?.items.find(x => x.diagnosis_id === selectedId)) : null;
  const date = value => new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' }).format(new Date(value));
  async function saved() {
    // Fetch this exact source after correction even if it moved to another concept.
    const current = await mapEvidence(classId, { student_id: selected.student_id, limit: 100 });
    setReviewedItem(current.items.find(x => x.diagnosis_id === selected.diagnosis_id) || null);
    await reload(); await onSaved();
  }
  return <section className="panel map-evidence" aria-labelledby="map-evidence-title">
    <h2 id="map-evidence-title">{selection.code || t(selection.uncertain_only ? 'mapUncertain' : 'mapPendingReviews')} · {t('mapResponses')}</h2>
    {selection.code && <Link className="button button-secondary" to={`/teacher/interventions?code=${encodeURIComponent(selection.code)}#groups`}>{t('mapGroupAction')}</Link>}
    {loading ? <LoadingState /> : error ? <ErrorState message={t('mapLoadFailed')} error={error} onRetry={reload} /> : <>
      {data.items.length ? <ul className="map-response-list">{data.items.map(item => <li key={item.diagnosis_id}>
        <div><strong>{item.student_code}</strong><p>{item.question_text}</p>
          <span>{item.review ? t(item.review.code === item.original_code ? 'mapTeacherReviewed' : 'mapTeacherCorrected') : t('mapAISuggested')} · {item.effective_code}{item.uncertain ? ` · ${t('mapUncertain')}` : ''}</span></div>
        <button className="button button-secondary" onClick={() => { setReviewedItem(null); setSelectedId(item.diagnosis_id); }} aria-label={t('mapInspectFor', { student: item.student_code })}>{t('mapInspect')}</button>
      </li>)}</ul> : <EmptyState title={t('mapNoMatches')} />}
      <div className="learning-actions" aria-label={t('mapPagination')}>
        <button className="button button-secondary" disabled={offset === 0} onClick={() => setOffset(x => Math.max(0, x - 20))}>{t('mapPreviousPage')}</button>
        <span>{t('mapPageCount', { from: data.total ? offset + 1 : 0, to: Math.min(offset + 20, data.total), total: data.total })}</span>
        <button className="button button-secondary" disabled={offset + 20 >= data.total} onClick={() => setOffset(x => x + 20)}>{t('mapNextPage')}</button>
      </div>
    </>}
    <Drawer open={Boolean(selected)} onClose={() => { setSelectedId(null); setReviewedItem(null); }} title={t('mapEvidenceTitle')}>
      {selected && <div className="map-response-detail">
        <h3>{selected.student_code} · {selected.effective_code}</h3>
        <p>{selected.question_text}</p>
        <dl>
          <dt>{t('mapStudentResponse')}</dt><dd>{selected.answer || t('noAnswer')}</dd>
          <dt>{t('mapStudentExplanation')}</dt><dd>{selected.student_explanation || t('mapEvidenceUnavailable')}</dd>
          <dt>{t('mapSubmittedAt')}</dt><dd>{date(selected.submitted_at)}</dd>
          <dt>{t('mapOriginalSuggestion')}</dt><dd>{selected.original_code} · {selected.provider}{selected.model_version ? ` · ${selected.model_version}` : ''}</dd>
          <dt>{t('mapSuggestedAt')}</dt><dd>{date(selected.suggested_at)}</dd>
          <dt>{t('mapSupportingQuote')}</dt><dd>{selected.evidence_quote || t('mapEvidenceUnavailable')}</dd>
          <dt>{t('mapAIExplanation')}</dt><dd>{selected.ai_explanation || t('mapEvidenceUnavailable')}</dd>
          <dt>{t('mapConfidence')}</dt><dd>{new Intl.NumberFormat(language, { maximumFractionDigits: 3 }).format(selected.confidence)}</dd>
        </dl>
        <p>{t('mapConfidenceHelp')}</p>
        <p>{selected.review ? t(selected.review.code === selected.original_code ? 'mapTeacherReviewed' : 'mapTeacherCorrected') : t('mapAISuggested')}</p>
        {selected.review && <div><strong>{selected.review.code}</strong><p>{selected.review.reason}</p><p>{date(selected.review.created_at)}</p></div>}
        {taxonomy.loading ? <LoadingState /> : taxonomy.error ? <ErrorState message={t('mapLoadFailed')} error={error} onRetry={taxonomy.reload} /> : <DiagnosisReview key={selected.diagnosis_id} diagnosisId={selected.diagnosis_id} originalCode={selected.original_code} codes={codes} onSaved={saved} />}
      </div>}
    </Drawer>
  </section>;
}
