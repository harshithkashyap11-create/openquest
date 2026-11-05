import { useI18n } from '../i18n/useI18n';
import { classDisplayName } from '../services/classDisplayName';
import {
  Check,
  ChevronRight,
  Clipboard,
  LoaderCircle,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

function inlineMarkdown(text, keyPrefix) {
  return String(text)
    .split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g)
    .map((part, index) => {
      const key = `${keyPrefix}-${index}`;
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={key}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={key}>{part.slice(1, -1)}</code>;
      }
      if (part.startsWith('*') && part.endsWith('*')) {
        return <em key={key}>{part.slice(1, -1)}</em>;
      }
      return part;
    });
}

function MarkdownReply({ content }) {
  const lines = String(content || '').split(/\r?\n/);
  const blocks = [];
  let paragraph = [];
  let index = 0;

  function flushParagraph() {
    if (paragraph.length) {
      blocks.push({ type: 'paragraph', lines: paragraph });
      paragraph = [];
    }
  }

  while (index < lines.length) {
    const line = lines[index];
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    const listItem = line.match(/^\s*(?:([-*])|(\d+)\.)\s+(.+)$/);

    if (!line.trim() || /^[-*_]{3,}$/.test(line.trim())) {
      flushParagraph();
      index += 1;
      continue;
    }
    if (heading) {
      flushParagraph();
      blocks.push({
        type: 'heading',
        level: heading[1].length,
        text: heading[2],
      });
      index += 1;
      continue;
    }
    if (listItem) {
      flushParagraph();
      const ordered = Boolean(listItem[2]);
      const items = [];
      while (index < lines.length) {
        const nextItem = lines[index].match(/^\s*(?:([-*])|(\d+)\.)\s+(.+)$/);
        if (!nextItem || Boolean(nextItem[2]) !== ordered) break;
        items.push(nextItem[3]);
        index += 1;
      }
      blocks.push({ type: ordered ? 'ordered-list' : 'unordered-list', items });
      continue;
    }

    paragraph.push(line.trim());
    index += 1;
  }
  flushParagraph();

  return (
    <div className="copilot-markdown">
      {blocks.map((block, blockIndex) => {
        if (block.type === 'heading') {
          return (
            <h3
              key={`heading-${blockIndex}`}
              className={block.level > 2 ? 'copilot-markdown-subheading' : ''}
            >
              {inlineMarkdown(block.text, `heading-${blockIndex}`)}
            </h3>
          );
        }
        if (block.type === 'ordered-list' || block.type === 'unordered-list') {
          const List = block.type === 'ordered-list' ? 'ol' : 'ul';
          return (
            <List key={`list-${blockIndex}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`list-${blockIndex}-${itemIndex}`}>
                  {inlineMarkdown(item, `list-${blockIndex}-${itemIndex}`)}
                </li>
              ))}
            </List>
          );
        }
        return (
          <p key={`paragraph-${blockIndex}`}>
            {block.lines.map((line, lineIndex) => (
              <span key={`paragraph-${blockIndex}-${lineIndex}`}>
                {lineIndex > 0 && <br />}
                {inlineMarkdown(line, `paragraph-${blockIndex}-${lineIndex}`)}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

export function ClassContext({
  context,
  loading,
  error,
  retryable,
  onRetry,
  taxonomy,
  classes,
  session,
  onSelectClass,
}) {
  const { t } = useI18n();
  const selectedTopic = taxonomy?.[context?.subject]?.find(
    (item) => item.topic === context?.topic,
  );
  const classOptions = (classes || []).filter(item => item.subject === (session.teachingSubject || session.subject));

  return (
    <section
      className="copilot-context"
      aria-label={t('Current classroom context')}
    >
      <div className="copilot-context-heading">
        <span className="copilot-context-indicator" aria-hidden="true" />
        <span>{t('CLASS CONTEXT')}</span>
      </div>
      {classOptions.length > 1 && (
        <label className="sr-only" htmlFor="copilot-class-picker">
          {t('Change active class')}
        </label>
      )}
      {classOptions.length > 1 ? (
        <select
          id="copilot-class-picker"
          className="copilot-class-picker"
          value={session.classId || ''}
          onChange={(event) => onSelectClass(event.target.value)}
          aria-label={t('Change active class')}
        >
          {classOptions.map((item) => (
            <option key={item.id} value={item.id}>
              {classDisplayName(item.class_name, item.topic)} · {item.subject} / {item.topic}
            </option>
          ))}
        </select>
      ) : (
        <strong className="copilot-context-class">
          {classDisplayName(context?.class_name, context?.topic) || session.className || 'Selected class'}
        </strong>
      )}
      <div className="copilot-context-tags">
        <span>
          {context?.subject || session.subject || 'Subject unavailable'}
        </span>
        <span aria-hidden="true">·</span>
        <span>{context?.topic || session.topic || 'Topic unavailable'}</span>
        {selectedTopic && (
          <span className="copilot-taxonomy-count">
            {selectedTopic.misconceptions.length} {t('patterns')}
          </span>
        )}
      </div>
      {loading && (
        <p className="copilot-context-status" role="status">
          <LoaderCircle size={13} className="copilot-spin" aria-hidden="true" />
          {t('Loading verified class context…')}
        </p>
      )}
      {error && (
        <div className="copilot-context-error" role="alert">
          <span>{error}</span>
          {retryable && (
            <button
              type="button"
              onClick={onRetry}
              aria-label={t('Retry loading class context')}
            >
              <RefreshCw size={14} aria-hidden="true" />
            </button>
          )}
        </div>
      )}
      {context && !loading && (
        <div
          className="copilot-context-metrics"
          aria-label={t('Verified class summary')}
        >
          <div>
            <strong>{context.total_students}</strong>
            <span>{t('ui.students')}</span>
          </div>
          <div>
            <strong>
              {context.submitted_students}/{context.total_students}
            </strong>
            <span>{t('ui.submitted')}</span>
          </div>
          <div>
            <strong>{context.pending_diagnoses}</strong>
            <span>{t('pending')}</span>
          </div>
        </div>
      )}
    </section>
  );
}

function ClassSummary({ summary }) {
  const { t } = useI18n();
  const stats = [
    { label: 'Students', value: summary.total_students },
    {
      label: 'Submitted',
      value: `${summary.submitted_students}/${summary.total_students}`,
    },
    { label: 'Diagnosed', value: summary.diagnosed_answers },
    { label: 'Pending', value: summary.pending_diagnoses },
  ];

  return (
    <section
      className="copilot-summary"
      aria-label={t('Verified classroom metrics')}
    >
      <div className="copilot-summary-grid">
        {stats.map((stat) => (
          <div className="copilot-summary-metric" key={t(stat.label)}>
            <strong>{stat.value}</strong>
            <span>{t(stat.label)}</span>
          </div>
        ))}
      </div>
      {(summary.baseline_accuracy != null ||
        summary.reassessment_accuracy != null) && (
        <div className="copilot-summary-scores">
          {summary.baseline_accuracy != null && (
            <span>
              {t('Initial')}
              <strong>{summary.baseline_accuracy}%</strong>
              <small>n={summary.baseline_sample_size}</small>
            </span>
          )}
          {summary.reassessment_accuracy != null && (
            <span>
              {t('Follow-up')}
              <strong>{summary.reassessment_accuracy}%</strong>
              <small>n={summary.reassessment_sample_size}</small>
            </span>
          )}
          {summary.accuracy_delta != null && (
            <span className="copilot-score-delta">
              {summary.accuracy_delta > 0 ? '+' : ''}
              {summary.accuracy_delta} {t('pp observed')}
            </span>
          )}
        </div>
      )}
      {summary.baseline_sample_size <= 1 &&
        summary.baseline_sample_size > 0 && (
          <p className="copilot-small-note">
            {t(
              'Initial accuracy reflects a small observed sample, not a measure of overall mastery.',
            )}
          </p>
        )}
    </section>
  );
}

function MisconceptionCards({ misconceptions }) {
  const { t } = useI18n();
  if (!misconceptions?.length) return null;
  return (
    <section
      className="copilot-misconceptions"
      aria-label={t('Observed misconception patterns')}
    >
      <h4>{t('Observed misconception patterns')}</h4>
      {misconceptions.slice(0, 3).map((item) => (
        <article className="copilot-misconception" key={item.code}>
          <div className="copilot-misconception-heading">
            <span className="copilot-code">{item.code}</span>
            <strong>{item.category}</strong>
            <span className="copilot-affected">
              {item.student_count} {t('ui.students')}
            </span>
          </div>
          <p>{item.description}</p>
          {item.sample_evidence?.[0] && (
            <blockquote>“{item.sample_evidence[0]}”</blockquote>
          )}
        </article>
      ))}
    </section>
  );
}

function DraftContent({ draft }) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const [copyMessage, setCopyMessage] = useState('');
  const copyTimer = useRef(null);
  useEffect(() => () => window.clearTimeout(copyTimer.current), []);

  async function copyDraft() {
    const parts = [
      draft.title,
      `Type: ${draft.content_type}`,
      draft.misconception_code ? `Target: ${draft.misconception_code}` : '',
      `Audience: ${draft.target_audience}`,
    ];
    if (draft.lesson_plan) {
      const plan = draft.lesson_plan;
      parts.push(
        `${plan.subject}: ${plan.topic} · ${plan.duration_minutes} minutes`,
        ...plan.objectives.map((item) => `Objective: ${item}`),
        ...plan.phases.map(
          (phase) =>
            `${phase.phase_name} (${phase.duration_minutes} min)\nTeacher: ${phase.teacher_action}\nStudents: ${phase.student_action}`,
        ),
        ...plan.materials_needed.map((item) => `Material: ${item}`),
        ...Object.entries(plan.differentiation || {}).map(
          ([level, detail]) => `${level}: ${detail}`,
        ),
        plan.assessment_check
          ? `Assessment check: ${plan.assessment_check}`
          : '',
      );
    }
    for (const [index, item] of (draft.items || []).entries()) {
      parts.push(
        `${index + 1}. ${item.question}`,
        item.options?.length ? `Options: ${item.options.join(' | ')}` : '',
        item.correct_answer ? `Answer: ${item.correct_answer}` : '',
        item.explanation ? `Explanation: ${item.explanation}` : '',
        ...(item.hints || []).map((hint) => `Hint: ${hint}`),
      );
    }
    if (draft.activity) {
      parts.push(
        draft.activity.activity_name,
        draft.activity.instructions,
        `Group size: ${draft.activity.group_size}`,
        ...draft.activity.materials_needed.map((item) => `Material: ${item}`),
        draft.activity.expected_takeaway,
      );
    }
    try {
      await navigator.clipboard.writeText(parts.filter(Boolean).join('\n\n'));
      setCopied(true);
      setCopyMessage('');
      window.clearTimeout(copyTimer.current);
      copyTimer.current = window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
      setCopyMessage(t('Clipboard access is unavailable in this browser.'));
    }
  }

  return (
    <section
      className="copilot-draft"
      aria-label={t('Generated educational draft')}
    >
      <div className="copilot-draft-banner">
        <span>
          <Sparkles size={14} aria-hidden="true" />{' '}
          {t('AI GENERATED DRAFT — TEACHER APPROVAL REQUIRED')}
        </span>
      </div>
      <div className="copilot-draft-title-row">
        <h3>{draft.title}</h3>
        <button
          type="button"
          className="copilot-copy-button"
          onClick={copyDraft}
        >
          {copied ? (
            <Check size={14} aria-hidden="true" />
          ) : (
            <Clipboard size={14} aria-hidden="true" />
          )}
          {copied ? t('Copied') : t('Copy')}
        </button>
      </div>
      <span className="sr-only" role="status">
        {copied ? t('Copied') : ''}
      </span>
      {copyMessage && (
        <p className="copilot-copy-error" role="status">
          {copyMessage}
        </p>
      )}
      {draft.misconception_code && (
        <span className="copilot-code">
          {t('Targets')} {draft.misconception_code}
        </span>
      )}
      {draft.lesson_plan && <LessonPlan plan={draft.lesson_plan} />}
      {draft.items?.length > 0 && (
        <div className="copilot-question-list">
          {draft.items.map((item, index) => (
            <article
              className="copilot-question-card"
              key={`${index}-${item.question}`}
            >
              <div className="copilot-question-heading">
                <span>
                  {t('QUESTION')} {String(index + 1).padStart(2, '0')}
                </span>
                {item.difficulty && <small>{item.difficulty}</small>}
              </div>
              <p>{item.question}</p>
              {item.options?.length > 0 && (
                <ul className="copilot-question-options">
                  {item.options.map((option) => (
                    <li key={option}>{option}</li>
                  ))}
                </ul>
              )}
              {item.targeted_misconception && (
                <span className="copilot-target-label">
                  {t('Focus:')} {item.targeted_misconception}
                </span>
              )}
              {(item.correct_answer || item.explanation) && (
                <details className="copilot-answer">
                  <summary>{t('Answer & explanation')}</summary>
                  {item.correct_answer && (
                    <p>
                      <strong>{t('Answer:')}</strong> {item.correct_answer}
                    </p>
                  )}
                  {item.explanation && <p>{item.explanation}</p>}
                </details>
              )}
              {item.hints?.length > 0 && (
                <details className="copilot-hints">
                  <summary>{t('Hints')}</summary>
                  <ul>
                    {item.hints.map((hint) => (
                      <li key={hint}>{hint}</li>
                    ))}
                  </ul>
                </details>
              )}
            </article>
          ))}
        </div>
      )}
      {draft.activity && (
        <article className="copilot-activity-card">
          <h4>{draft.activity.activity_name}</h4>
          <p>{draft.activity.instructions}</p>
          {draft.activity.materials_needed?.length > 0 && (
            <p>
              <strong>{t('Materials:')}</strong>{' '}
              {draft.activity.materials_needed.join(', ')}
            </p>
          )}
          {draft.activity.expected_takeaway && (
            <p>
              <strong>{t('Expected takeaway:')}</strong>{' '}
              {draft.activity.expected_takeaway}
            </p>
          )}
        </article>
      )}
    </section>
  );
}

function LessonPlan({ plan }) {
  const { t } = useI18n();
  return (
    <section className="copilot-lesson-plan">
      <div className="copilot-lesson-meta">
        <span>
          {plan.subject} · {plan.topic}
        </span>
        <strong>
          {plan.duration_minutes} {t('min')}
        </strong>
      </div>
      {plan.objectives?.length > 0 && (
        <div className="copilot-plan-section">
          <h4>{t('Learning objectives')}</h4>
          <ul>
            {plan.objectives.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {plan.phases?.length > 0 && (
        <div className="copilot-timeline">
          {plan.phases.map((phase, index) => (
            <article
              className="copilot-phase"
              key={`${phase.phase_name}-${index}`}
            >
              <span className="copilot-phase-marker">{index + 1}</span>
              <div>
                <div className="copilot-phase-title">
                  <strong>{phase.phase_name}</strong>
                  <span>
                    {phase.duration_minutes} {t('min')}
                  </span>
                </div>
                <p>
                  <b>{t('Teacher')}</b> {phase.teacher_action}
                </p>
                <p>
                  <b>{t('Students')}</b> {phase.student_action}
                </p>
              </div>
            </article>
          ))}
        </div>
      )}
      {plan.materials_needed?.length > 0 && (
        <div className="copilot-plan-section">
          <h4>{t('Materials')}</h4>
          <p>{plan.materials_needed.join(' · ')}</p>
        </div>
      )}
      {Object.keys(plan.differentiation || {}).length > 0 && (
        <details className="copilot-differentiation">
          <summary>{t('Differentiation')}</summary>
          {Object.entries(plan.differentiation).map(([level, detail]) => (
            <p key={level}>
              <strong>{level}:</strong> {detail}
            </p>
          ))}
        </details>
      )}
      {plan.assessment_check && (
        <div className="copilot-plan-assessment">
          <strong>{t('Assessment check')}</strong>
          <p>{plan.assessment_check}</p>
        </div>
      )}
    </section>
  );
}

function AssistantResponse({ response, onFollowup }) {
  const { t } = useI18n();
  const providerName =
    {
      openrouter: 'OpenRouter',
      gemini: 'Gemini',
      gemini_fallback: 'Gemini template fallback',
      mock: 'Mock provider',
      mock_fallback: 'Mock fallback',
      openrouter_fallback: 'OpenRouter fallback',
    }[response.provider] || response.provider;
  const reply = response.reply?.trim() || '';
  const replyRepeatsDraft = Boolean(
    response.draft_content?.title &&
    reply.toLowerCase().includes(response.draft_content.title.toLowerCase()),
  );

  return (
    <>
      <div className="copilot-provider-line">
        <span className="copilot-provider-dot" aria-hidden="true" />
        {t(providerName || 'provider')}
        {response.model_version && <span>· {response.model_version}</span>}
      </div>
      {response.draft_content && (
        <DraftContent draft={response.draft_content} />
      )}
      {reply && !replyRepeatsDraft && <MarkdownReply content={reply} />}
      {response.class_context_summary && (
        <>
          <ClassSummary summary={response.class_context_summary} />
          <MisconceptionCards
            misconceptions={response.class_context_summary.top_misconceptions}
          />
        </>
      )}
      {response.suggested_followups?.length > 0 && (
        <div className="copilot-followups">
          <span>{t('Continue with')}</span>
          {response.suggested_followups.map((prompt) => (
            <button
              type="button"
              key={prompt}
              onClick={() => onFollowup(prompt)}
            >
              {prompt}
              <ChevronRight size={13} aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
    </>
  );
}

export function AssistantMessage({ message, onFollowup }) {
  const { t } = useI18n();
  return (
    <article className="copilot-message copilot-message-assistant">
      <span className="copilot-message-avatar" aria-hidden="true">
        <Sparkles size={14} />
      </span>
      <div className="copilot-message-body">
        <div className="copilot-message-label">{t('Teacher Copilot')}</div>
        <div className="copilot-message-content">
          {message.response ? (
            <AssistantResponse
              response={message.response}
              onFollowup={onFollowup}
            />
          ) : (
            <MarkdownReply content={message.content} />
          )}
        </div>
      </div>
    </article>
  );
}

export function UserMessage({ content }) {
  const { t } = useI18n();
  return (
    <article className="copilot-message copilot-message-user">
      <div className="copilot-message-body">
        <div className="copilot-message-label">{t('You')}</div>
        <div className="copilot-user-bubble">{content}</div>
      </div>
    </article>
  );
}
