import { useI18n } from '../i18n/useI18n';

export function EvidenceState({ state }) {
  const { t } = useI18n();
  return <article className="panel learning-evidence">
    <p className="eyebrow">{state.subject} · {state.topic}</p>
    <h3>{t('masteryIndicator')}: {state.mastery_category.replaceAll('_', ' ')}</h3>
    <p>{t('evidenceCount', { count: state.independent_evidence_count })} · {t('hintsViewed', { count: state.hint_count })}</p>
    <p className="field-help">{t('heuristicCaution')}</p>
    <p>{t('recommendedLevel')}: {state.difficulty} · {state.session_state.replaceAll('_', ' ')}</p>
    {state.active_misconceptions.length > 0 && <p>{t('learningGaps')}: {state.active_misconceptions.join(', ')}</p>}
    {state.decision && <blockquote><strong>{state.decision.action.replaceAll('_', ' ')}</strong><p>{state.decision.reason}</p>
      {state.decision.requires_teacher_approval && <span className="code-pill">{t('teacherReviewRequired')}</span>}</blockquote>}
    <details><summary>{t('evidenceHistory')} ({state.events.length})</summary><ol>
      {state.events.map(event => <li key={event.id}><strong>{event.kind.replaceAll('_', ' ')}</strong>
        <p>{event.data.evidence || event.data.reason || event.data.hint || event.data.next || event.data.code || ''}</p>
        {event.data.provider && <p>{event.data.provider} · {event.data.model || t('noLiveInference')}</p>}
        <small>{event.created_at}</small></li>)}
    </ol></details>
  </article>;
}

export function LessonReader({ lesson }) {
  const { t } = useI18n();
  const { content, language } = lesson.revision;
  return <article className="learning-lesson" lang={language}>
    <h3>{content.title}</h3>
    <p><span className="code-pill">{lesson.revision.status}</span> · <span>{lesson.revision.provider}</span> · {lesson.revision.model || t('noLiveInference')}</p>
    <p className="field-help">{lesson.revision.generation_note}</p>
    <ul>{content.objectives.map((o, i) => <li key={i}>{o}</li>)}</ul>
    <p className="lesson-prose">{content.explanation}</p>
    <h4>{t('misconceptionCorrection')}</h4><p>{content.misconception_correction}</p>
    <h4>{t('workedExample')}</h4><p>{content.worked_example.problem}</p>
    <ol>{content.worked_example.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
    <p>{content.worked_example.answer}</p>
    <h4>{t('practiceQuestions')}</h4><ol>{content.practice_questions.map((q, i) => <li key={i}>{q.prompt}{q.answer && <p>{t('answerKey')}: {q.answer}</p>}</li>)}</ol>
    <h4>{t('exitTicket')}</h4><p>{content.exit_ticket.prompt}</p>
    {content.exit_ticket.answer && <p>{t('answerKey')}: {content.exit_ticket.answer}</p>}
  </article>;
}
