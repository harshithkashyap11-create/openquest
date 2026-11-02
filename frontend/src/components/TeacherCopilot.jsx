import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowUpRight,
  BookOpenCheck,
  Check,
  ChevronDown,
  ChevronRight,
  Clipboard,
  FileText,
  Lightbulb,
  LoaderCircle,
  MessageSquareText,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
  UsersRound,
  X,
} from 'lucide-react';
import { getErrorMessage } from '../services/api';
import {
  chatWithCopilot,
  getCopilotClassContext,
  getCopilotTaxonomy,
  listDemoClasses,
} from '../services/classpulseApi';
import './TeacherCopilot.css';

const QUICK_ACTIONS = [
  {
    label: 'Analyze my class',
    prompt: 'Analyze my class using the current assessment and diagnosis data. Summarize the observed patterns and sample sizes.',
    action: 'summarize_class',
    icon: MessageSquareText,
  },
  {
    label: 'Explain biggest misconception',
    prompt: 'Explain the most common misconception in this class, using the recorded evidence and a clear teaching response.',
    action: 'summarize_class',
    icon: Lightbulb,
  },
  {
    label: 'Generate a lesson plan',
    prompt: 'Create a differentiated 45-minute lesson plan for this class and topic.',
    action: 'lesson_plan',
    icon: BookOpenCheck,
  },
  {
    label: 'Create a targeted worksheet',
    prompt: 'Create a targeted worksheet for this class topic and its most common observed misconception, with answers and explanations.',
    action: 'generate_worksheet',
    icon: FileText,
  },
  {
    label: 'Recommend teaching strategies',
    prompt: 'Recommend practical, evidence-informed teaching strategies for this class and topic.',
    action: null,
    icon: Lightbulb,
  },
  {
    label: 'Generate practice questions',
    prompt: 'Generate practice questions for this class topic, including correct answers and explanations.',
    action: 'generate_worksheet',
    icon: Clipboard,
  },
  {
    label: 'Identify students needing attention',
    prompt: 'Identify students needing attention based on the recorded classroom evidence and explain why.',
    action: 'struggling_students',
    icon: UsersRound,
  },
  {
    label: 'Compare intervention outcomes',
    prompt: 'Compare intervention and reassessment outcomes for this class, including the sample sizes and observed score change.',
    action: 'compare_outcomes',
    icon: ArrowUpRight,
  },
];

const STARTER_PROMPTS = [
  {
    label: 'What is the class showing?',
    message: 'Summarize what the current class data shows, including sample sizes and any important limitations.',
    action: 'summarize_class',
  },
  {
    label: 'Plan a focused lesson',
    message: 'Create a differentiated lesson plan focused on the most important learning need in this class.',
    action: 'lesson_plan',
  },
  {
    label: 'Build a quick check',
    message: 'Create a short set of practice questions for this topic with answers and explanations.',
    action: 'generate_worksheet',
  },
];
const EMPTY_CHAT_STATE = {
  key: '',
  messages: [],
  sending: false,
  error: '',
  retryRequest: null,
};

function inlineMarkdown(text, keyPrefix) {
  return String(text).split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g).map((part, index) => {
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
      blocks.push({ type: 'heading', level: heading[1].length, text: heading[2] });
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
            <h3 key={`heading-${blockIndex}`} className={block.level > 2 ? 'copilot-markdown-subheading' : ''}>
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

function ClassContext({
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
  const selectedTopic = taxonomy?.[context?.subject]?.find(
    (item) => item.topic === context?.topic,
  );
  const classOptions = classes || [];

  return (
    <section className="copilot-context" aria-label="Current classroom context">
      <div className="copilot-context-heading">
        <span className="copilot-context-indicator" aria-hidden="true" />
        <span>CLASS CONTEXT</span>
      </div>
      {classOptions.length > 1 && (
        <label className="sr-only" htmlFor="copilot-class-picker">Change active class</label>
      )}
      {classOptions.length > 1 ? (
        <select
          id="copilot-class-picker"
          className="copilot-class-picker"
          value={session.classId || ''}
          onChange={(event) => onSelectClass(event.target.value)}
          aria-label="Change active class"
        >
          {classOptions.map((item) => (
            <option key={item.id} value={item.id}>
              {item.class_name} · {item.subject} / {item.topic}
            </option>
          ))}
        </select>
      ) : (
        <strong className="copilot-context-class">
          {context?.class_name || session.className || 'Selected class'}
        </strong>
      )}
      <div className="copilot-context-tags">
        <span>{context?.subject || session.subject || 'Subject unavailable'}</span>
        <span aria-hidden="true">·</span>
        <span>{context?.topic || session.topic || 'Topic unavailable'}</span>
        {selectedTopic && (
          <span className="copilot-taxonomy-count">
            {selectedTopic.misconceptions.length} patterns
          </span>
        )}
      </div>
      {loading && (
        <p className="copilot-context-status" role="status">
          <LoaderCircle size={13} className="copilot-spin" aria-hidden="true" />
          Loading verified class context…
        </p>
      )}
      {error && (
        <div className="copilot-context-error" role="alert">
          <span>{error}</span>
          {retryable && (
            <button type="button" onClick={onRetry} aria-label="Retry loading class context">
              <RefreshCw size={14} aria-hidden="true" />
            </button>
          )}
        </div>
      )}
      {context && !loading && (
        <div className="copilot-context-metrics" aria-label="Verified class summary">
          <div>
            <strong>{context.total_students}</strong>
            <span>students</span>
          </div>
          <div>
            <strong>{context.submitted_students}/{context.total_students}</strong>
            <span>submitted</span>
          </div>
          <div>
            <strong>{context.pending_diagnoses}</strong>
            <span>pending</span>
          </div>
        </div>
      )}
    </section>
  );
}

function ClassSummary({ summary }) {
  const stats = [
    { label: 'Students', value: summary.total_students },
    { label: 'Submitted', value: `${summary.submitted_students}/${summary.total_students}` },
    { label: 'Diagnosed', value: summary.diagnosed_answers },
    { label: 'Pending', value: summary.pending_diagnoses },
  ];

  return (
    <section className="copilot-summary" aria-label="Verified classroom metrics">
      <div className="copilot-summary-grid">
        {stats.map((stat) => (
          <div className="copilot-summary-metric" key={stat.label}>
            <strong>{stat.value}</strong>
            <span>{stat.label}</span>
          </div>
        ))}
      </div>
      {(summary.baseline_accuracy != null || summary.reassessment_accuracy != null) && (
        <div className="copilot-summary-scores">
          {summary.baseline_accuracy != null && (
            <span>
              Initial <strong>{summary.baseline_accuracy}%</strong>
              <small>n={summary.baseline_sample_size}</small>
            </span>
          )}
          {summary.reassessment_accuracy != null && (
            <span>
              Follow-up <strong>{summary.reassessment_accuracy}%</strong>
              <small>n={summary.reassessment_sample_size}</small>
            </span>
          )}
          {summary.accuracy_delta != null && (
            <span className="copilot-score-delta">
              {summary.accuracy_delta > 0 ? '+' : ''}{summary.accuracy_delta} pp observed
            </span>
          )}
        </div>
      )}
      {summary.baseline_sample_size <= 1 && summary.baseline_sample_size > 0 && (
        <p className="copilot-small-note">
          Initial accuracy reflects a small observed sample, not a measure of overall mastery.
        </p>
      )}
    </section>
  );
}

function MisconceptionCards({ misconceptions }) {
  if (!misconceptions?.length) return null;
  return (
    <section className="copilot-misconceptions" aria-label="Observed misconception patterns">
      <h4>Observed misconception patterns</h4>
      {misconceptions.slice(0, 3).map((item) => (
        <article className="copilot-misconception" key={item.code}>
          <div className="copilot-misconception-heading">
            <span className="copilot-code">{item.code}</span>
            <strong>{item.category}</strong>
            <span className="copilot-affected">{item.student_count} students</span>
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
  const [copied, setCopied] = useState(false);
  const [copyMessage, setCopyMessage] = useState('');

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
          (phase) => `${phase.phase_name} (${phase.duration_minutes} min)\nTeacher: ${phase.teacher_action}\nStudents: ${phase.student_action}`,
        ),
        ...plan.materials_needed.map((item) => `Material: ${item}`),
        ...Object.entries(plan.differentiation || {}).map(
          ([level, detail]) => `${level}: ${detail}`,
        ),
        plan.assessment_check ? `Assessment check: ${plan.assessment_check}` : '',
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
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
      setCopyMessage('Clipboard access is unavailable in this browser.');
    }
  }

  return (
    <section className="copilot-draft" aria-label="Generated educational draft">
      <div className="copilot-draft-banner">
        <span><Sparkles size={14} aria-hidden="true" /> AI GENERATED DRAFT — TEACHER APPROVAL REQUIRED</span>
      </div>
      <div className="copilot-draft-title-row">
        <h3>{draft.title}</h3>
        <button type="button" className="copilot-copy-button" onClick={copyDraft}>
          {copied ? <Check size={14} aria-hidden="true" /> : <Clipboard size={14} aria-hidden="true" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      {copyMessage && <p className="copilot-copy-error" role="status">{copyMessage}</p>}
      {draft.misconception_code && (
        <span className="copilot-code">Targets {draft.misconception_code}</span>
      )}
      {draft.lesson_plan && <LessonPlan plan={draft.lesson_plan} />}
      {draft.items?.length > 0 && (
        <div className="copilot-question-list">
          {draft.items.map((item, index) => (
            <article className="copilot-question-card" key={`${index}-${item.question}`}>
              <div className="copilot-question-heading">
                <span>QUESTION {String(index + 1).padStart(2, '0')}</span>
                {item.difficulty && <small>{item.difficulty}</small>}
              </div>
              <p>{item.question}</p>
              {item.options?.length > 0 && (
                <ul className="copilot-question-options">
                  {item.options.map((option) => <li key={option}>{option}</li>)}
                </ul>
              )}
              {item.targeted_misconception && (
                <span className="copilot-target-label">Focus: {item.targeted_misconception}</span>
              )}
              {(item.correct_answer || item.explanation) && (
                <details className="copilot-answer">
                  <summary>Answer &amp; explanation</summary>
                  {item.correct_answer && <p><strong>Answer:</strong> {item.correct_answer}</p>}
                  {item.explanation && <p>{item.explanation}</p>}
                </details>
              )}
              {item.hints?.length > 0 && (
                <details className="copilot-hints">
                  <summary>Hints</summary>
                  <ul>{item.hints.map((hint) => <li key={hint}>{hint}</li>)}</ul>
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
            <p><strong>Materials:</strong> {draft.activity.materials_needed.join(', ')}</p>
          )}
          {draft.activity.expected_takeaway && (
            <p><strong>Expected takeaway:</strong> {draft.activity.expected_takeaway}</p>
          )}
        </article>
      )}
    </section>
  );
}

function LessonPlan({ plan }) {
  return (
    <section className="copilot-lesson-plan">
      <div className="copilot-lesson-meta">
        <span>{plan.subject} · {plan.topic}</span>
        <strong>{plan.duration_minutes} min</strong>
      </div>
      {plan.objectives?.length > 0 && (
        <div className="copilot-plan-section">
          <h4>Learning objectives</h4>
          <ul>{plan.objectives.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      )}
      {plan.phases?.length > 0 && (
        <div className="copilot-timeline">
          {plan.phases.map((phase, index) => (
            <article className="copilot-phase" key={`${phase.phase_name}-${index}`}>
              <span className="copilot-phase-marker">{index + 1}</span>
              <div>
                <div className="copilot-phase-title">
                  <strong>{phase.phase_name}</strong>
                  <span>{phase.duration_minutes} min</span>
                </div>
                <p><b>Teacher</b> {phase.teacher_action}</p>
                <p><b>Students</b> {phase.student_action}</p>
              </div>
            </article>
          ))}
        </div>
      )}
      {plan.materials_needed?.length > 0 && (
        <div className="copilot-plan-section">
          <h4>Materials</h4>
          <p>{plan.materials_needed.join(' · ')}</p>
        </div>
      )}
      {Object.keys(plan.differentiation || {}).length > 0 && (
        <details className="copilot-differentiation">
          <summary>Differentiation</summary>
          {Object.entries(plan.differentiation).map(([level, detail]) => (
            <p key={level}><strong>{level}:</strong> {detail}</p>
          ))}
        </details>
      )}
      {plan.assessment_check && (
        <div className="copilot-plan-assessment">
          <strong>Assessment check</strong>
          <p>{plan.assessment_check}</p>
        </div>
      )}
    </section>
  );
}

function AssistantResponse({ response, onFollowup }) {
  const providerName = {
    openrouter: 'OpenRouter',
    mock: 'Mock provider',
    mock_fallback: 'Mock fallback',
    openrouter_fallback: 'OpenRouter fallback',
  }[response.provider] || response.provider;
  const reply = response.reply?.trim() || '';
  const replyRepeatsDraft = Boolean(
    response.draft_content?.title
    && reply.toLowerCase().includes(response.draft_content.title.toLowerCase()),
  );

  return (
    <>
      <div className="copilot-provider-line">
        <span className="copilot-provider-dot" aria-hidden="true" />
        {providerName || 'AI provider'}
        {response.model_version && <span>· {response.model_version}</span>}
      </div>
      {response.draft_content && <DraftContent draft={response.draft_content} />}
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
          <span>Continue with</span>
          {response.suggested_followups.map((prompt) => (
            <button type="button" key={prompt} onClick={() => onFollowup(prompt)}>
              {prompt}<ChevronRight size={13} aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function AssistantMessage({ message, onFollowup }) {
  return (
    <article className="copilot-message copilot-message-assistant">
      <span className="copilot-message-avatar" aria-hidden="true">
        <Sparkles size={14} />
      </span>
      <div className="copilot-message-body">
        <div className="copilot-message-label">Teacher Copilot</div>
        <div className="copilot-message-content">
          {message.response ? (
            <AssistantResponse response={message.response} onFollowup={onFollowup} />
          ) : (
            <MarkdownReply content={message.content} />
          )}
        </div>
      </div>
    </article>
  );
}

function UserMessage({ content }) {
  return (
    <article className="copilot-message copilot-message-user">
      <div className="copilot-message-body">
        <div className="copilot-message-label">You</div>
        <div className="copilot-user-bubble">{content}</div>
      </div>
    </article>
  );
}

export default function TeacherCopilot({ session, startSession }) {
  const [isOpen, setIsOpen] = useState(() => !window.matchMedia('(max-width: 1100px)').matches);
  const [isCompact, setIsCompact] = useState(() => window.matchMedia('(max-width: 1100px)').matches);
  const [classes, setClasses] = useState([]);
  const [classesLoading, setClassesLoading] = useState(true);
  const [classesError, setClassesError] = useState('');
  const [taxonomy, setTaxonomy] = useState(null);
  const [contextState, setContextState] = useState({
    key: '',
    data: null,
    loading: false,
    error: '',
  });
  const [chatState, setChatState] = useState(EMPTY_CHAT_STATE);
  const [inputState, setInputState] = useState({ key: '', value: '' });
  const messagesEndRef = useRef(null);
  const panelRef = useRef(null);
  const closeButtonRef = useRef(null);
  const triggerRef = useRef(null);
  const compactWasOpen = useRef(false);
  const chatRequestId = useRef(0);
  const contextKey = `${session.classId || ''}:${session.subject || ''}:${session.topic || ''}`;
  const contextKeyRef = useRef(contextKey);
  const currentContextState = contextState.key === contextKey ? contextState : null;
  const context = currentContextState?.data || null;
  const contextLoading = Boolean(session.classId) && (
    !currentContextState || currentContextState.loading
  );
  const contextError = session.classId
    ? currentContextState?.error || ''
    : 'Select a class to load its verified classroom context.';
  const currentChat = chatState.key === contextKey ? chatState : EMPTY_CHAT_STATE;
  const messages = currentChat.messages;
  const sending = currentChat.sending;
  const chatError = currentChat.error;
  const retryRequest = currentChat.retryRequest;
  const input = inputState.key === contextKey ? inputState.value : '';

  useLayoutEffect(() => {
    contextKeyRef.current = contextKey;
    chatRequestId.current += 1;
  }, [contextKey]);

  const activeTopic = useMemo(
    () => taxonomy?.[context?.subject]?.find((item) => item.topic === context?.topic),
    [context, taxonomy],
  );
  const starterPrompts = useMemo(() => {
    if (!activeTopic?.misconceptions?.length) return STARTER_PROMPTS;
    const misconception = activeTopic.misconceptions[0];
    return [
      {
        label: `Explain ${misconception.code}`,
        message: `Explain the ${misconception.code} misconception (${misconception.category}) for ${context.topic}, then suggest a clear way to teach it.`,
        action: 'summarize_class',
      },
      ...STARTER_PROMPTS.slice(0, 2),
    ];
  }, [activeTopic, context]);

  useEffect(() => {
    let active = true;
    listDemoClasses()
      .then((result) => {
        if (active) {
          setClasses(Array.isArray(result) ? result : []);
          setClassesError('');
        }
      })
      .catch((error) => {
        if (active) setClassesError(getErrorMessage(error, 'Could not load classes.'));
      })
      .finally(() => {
        if (active) setClassesLoading(false);
      });
    getCopilotTaxonomy()
      .then((result) => {
        if (active && result && typeof result === 'object') setTaxonomy(result);
      })
      .catch(() => {
        if (active) setTaxonomy(null);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    if (!session.classId) return undefined;
    getCopilotClassContext(session.classId)
      .then((result) => {
        if (!active) return;
        if (!result || result.class_id !== session.classId) {
          throw new Error('The backend returned a different class context.');
        }
        setContextState({ key: contextKey, data: result, loading: false, error: '' });
      })
      .catch((error) => {
        if (active) {
          setContextState({
            key: contextKey,
            data: null,
            loading: false,
            error: getErrorMessage(error, error.message || 'Could not load this class context.'),
          });
        }
      });
    return () => {
      active = false;
    };
  }, [contextKey, session.classId]);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 1100px)');
    const updateCompact = (event) => {
      setIsCompact(event.matches);
      if (event.matches) setIsOpen(false);
      else setIsOpen(true);
    };
    media.addEventListener('change', updateCompact);
    return () => media.removeEventListener('change', updateCompact);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' });
  }, [messages, sending]);

  useEffect(() => {
    if (isCompact && isOpen) {
      closeButtonRef.current?.focus();
      compactWasOpen.current = true;
      return;
    }
    if (isCompact && compactWasOpen.current) {
      triggerRef.current?.focus();
      compactWasOpen.current = false;
    }
  }, [isCompact, isOpen]);

  useEffect(() => {
    if (!isCompact || !isOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
        return;
      }
      if (event.key === 'Tab' && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll(
          'button:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [href]',
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [isCompact, isOpen]);

  function selectClass(classId) {
    const selected = classes.find((item) => item.id === classId);
    if (!selected || selected.id === session.classId) return;
    startSession({
      ...session,
      classId: selected.id,
      className: selected.class_name,
      subject: selected.subject,
      topic: selected.topic,
    });
  }

  function retryContext() {
    if (classesError) {
      setClassesLoading(true);
      setClassesError('');
      listDemoClasses()
        .then((result) => setClasses(Array.isArray(result) ? result : []))
        .catch((error) => setClassesError(getErrorMessage(error, 'Could not load classes.')))
        .finally(() => setClassesLoading(false));
    }
    if (!session.classId) return;
    setContextState({ key: contextKey, data: null, loading: true, error: '' });
    getCopilotClassContext(session.classId)
      .then((result) => {
        if (result?.class_id !== session.classId) {
          throw new Error('The backend returned a different class context.');
        }
        setContextState({ key: contextKey, data: result, loading: false, error: '' });
      })
      .catch((error) => {
        setContextState({
          key: contextKey,
          data: null,
          loading: false,
          error: getErrorMessage(error, error.message || 'Could not load this class context.'),
        });
      });
  }

  async function sendRequest(request, history, { appendUser = true } = {}) {
    if (!context || contextLoading || contextError || sending) return;
    const currentId = ++chatRequestId.current;
    const requestKey = contextKey;
    const requestContext = {
      message: request.message,
      action: request.action || null,
      history,
    };
    setChatState((current) => {
      const base = current.key === requestKey
        ? current
        : { ...EMPTY_CHAT_STATE, key: requestKey };
      return {
        ...base,
        messages: appendUser
          ? [...base.messages, { id: `user-${currentId}`, role: 'user', content: request.message }]
          : base.messages,
        sending: true,
        error: '',
        retryRequest: null,
      };
    });
    try {
      const response = await chatWithCopilot({
        message: requestContext.message,
        classId: context.class_id,
        subject: context.subject,
        topic: context.topic,
        history: requestContext.history,
        action: requestContext.action,
      });
      if (currentId !== chatRequestId.current || contextKeyRef.current !== requestKey) return;
      if (
        !response
        || typeof response.reply !== 'string'
        || (!response.reply.trim() && !response.draft_content && !response.class_context_summary)
      ) {
        throw new Error('The assistant returned an empty response. Please try again.');
      }
      setChatState((current) => (
        current.key === requestKey
          ? {
              ...current,
              messages: [...current.messages, {
                id: `assistant-${currentId}`,
                role: 'assistant',
                response,
              }],
            }
          : current
      ));
    } catch (error) {
      if (currentId !== chatRequestId.current || contextKeyRef.current !== requestKey) return;
      setChatState((current) => (
        current.key === requestKey
          ? {
              ...current,
              error: error.message === 'The assistant returned an empty response. Please try again.'
                ? error.message
                : getErrorMessage(error, 'The assistant could not respond. Please try again.'),
              retryRequest: { ...requestContext },
            }
          : current
      ));
    } finally {
      if (currentId === chatRequestId.current && contextKeyRef.current === requestKey) {
        setChatState((current) => (
          current.key === requestKey ? { ...current, sending: false } : current
        ));
      }
    }
  }

  function submitPrompt(message, action = null) {
    const cleanedMessage = message.trim();
    if (!cleanedMessage || sending || !context || contextError) return;
    const history = messages
      .filter((item) => item.role === 'user' || item.role === 'assistant')
      .map((item) => ({
        role: item.role,
        content: item.role === 'assistant' ? item.response?.reply || item.content || '' : item.content,
      }))
      .filter((item) => item.content.trim());
    setInputState({ key: contextKey, value: '' });
    void sendRequest({ message: cleanedMessage, action }, history);
  }

  function retryLastRequest() {
    if (!retryRequest || sending) return;
    void sendRequest(retryRequest, retryRequest.history, { appendUser: false });
  }

  function clearConversation() {
    if (sending) return;
    chatRequestId.current += 1;
    setChatState({ ...EMPTY_CHAT_STATE, key: contextKey });
    setInputState({ key: contextKey, value: '' });
  }

  function openPanel() {
    triggerRef.current?.focus();
    setIsOpen(true);
  }

  function closePanel() {
    setIsOpen(false);
  }

  const canSend = Boolean(
    context
    && !contextLoading
    && !contextError
    && input.trim()
    && !sending,
  );

  return (
    <>
      {isCompact && isOpen && (
        <button
          type="button"
          className="copilot-backdrop"
          aria-label="Close Teacher Copilot"
          aria-hidden="true"
          tabIndex={-1}
          onClick={closePanel}
        />
      )}
      <aside
        ref={panelRef}
        className={`copilot-panel${isOpen ? ' is-open' : ''}${isCompact ? ' is-compact' : ''}`}
        role={isCompact && isOpen ? 'dialog' : 'complementary'}
        aria-modal={isCompact && isOpen ? 'true' : undefined}
        aria-label="Teacher Copilot"
        aria-labelledby={isOpen ? 'copilot-title' : undefined}
        aria-hidden={isCompact && !isOpen ? 'true' : undefined}
      >
        {isOpen ? (
          <>
            <header className="copilot-header">
              <div className="copilot-brand">
                <span className="copilot-brand-mark" aria-hidden="true">
                  <Sparkles size={17} />
                </span>
                <div>
                  <h2 id="copilot-title">Teacher Copilot</h2>
                  <span>Classroom-grounded assistant</span>
                </div>
              </div>
              <div className="copilot-header-actions">
                <button
                  type="button"
                  className="copilot-icon-button"
                  onClick={clearConversation}
                  disabled={!messages.length || sending}
                  aria-label="Clear conversation"
                  title="Clear conversation"
                >
                  <Trash2 size={16} aria-hidden="true" />
                </button>
                <button
                  ref={closeButtonRef}
                  type="button"
                  className="copilot-icon-button"
                  onClick={closePanel}
                  aria-label={isCompact ? 'Close Teacher Copilot' : 'Collapse Teacher Copilot'}
                  title={isCompact ? 'Close assistant' : 'Collapse assistant'}
                >
                  {isCompact
                    ? <X size={17} aria-hidden="true" />
                    : <PanelRightClose size={17} aria-hidden="true" />}
                </button>
              </div>
            </header>

            <div className="copilot-context-wrap">
              <ClassContext
                context={context}
                loading={contextLoading}
                error={contextError || classesError}
                retryable={Boolean(session.classId || classesError)}
                onRetry={retryContext}
                taxonomy={taxonomy}
                classes={classes}
                session={session}
                onSelectClass={selectClass}
              />
              {classesLoading && (
                <span className="copilot-class-list-loading" role="status">
                  <LoaderCircle size={12} className="copilot-spin" aria-hidden="true" />
                  Loading classes…
                </span>
              )}
            </div>

            <div className="copilot-conversation" aria-label="Copilot conversation">
              {messages.length === 0 && (
                <section className="copilot-welcome">
                  <span className="copilot-welcome-mark" aria-hidden="true">
                    <Sparkles size={18} />
                  </span>
                  <h3>What would you like to work on?</h3>
                  <p>
                    Responses use the selected class context. Generated resources are drafts for your review.
                  </p>
                  {!contextLoading && !contextError && context && (
                    <div className="copilot-starter-prompts">
                      {starterPrompts.map((prompt) => (
                        <button
                          type="button"
                          key={prompt.label}
                          onClick={() => submitPrompt(prompt.message, prompt.action)}
                          disabled={!context || sending}
                        >
                          {prompt.label}<ChevronRight size={14} aria-hidden="true" />
                        </button>
                      ))}
                    </div>
                  )}
                  {contextError && !contextLoading && (
                    <p className="copilot-empty-context">
                      Load a valid class context to start a grounded conversation.
                    </p>
                  )}
                </section>
              )}
              {messages.map((message) => (
                message.role === 'user'
                  ? <UserMessage key={message.id} content={message.content} />
                  : (
                    <AssistantMessage
                      key={message.id}
                      message={message}
                      onFollowup={(prompt) => submitPrompt(prompt)}
                    />
                  )
              ))}
              {sending && (
                <div className="copilot-loading" role="status" aria-live="polite">
                  <span className="copilot-message-avatar" aria-hidden="true"><Sparkles size={14} /></span>
                  <span className="copilot-loading-dots"><i /><i /><i /></span>
                  <span>Working with your class context…</span>
                </div>
              )}
              {chatError && (
                <div className="copilot-chat-error" role="alert">
                  <div>
                    <strong>Couldn’t get a response</strong>
                    <p>{chatError}</p>
                  </div>
                  <button type="button" onClick={retryLastRequest} disabled={!retryRequest || sending}>
                    <RefreshCw size={14} aria-hidden="true" /> Retry
                  </button>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {messages.length > 0 && (
              <details className="copilot-quick-actions">
                <summary>
                  <span><Sparkles size={14} aria-hidden="true" /> Quick actions</span>
                  <ChevronDown size={14} aria-hidden="true" />
                </summary>
                <div className="copilot-action-grid">
                  {QUICK_ACTIONS.map(({ label, prompt, action, icon: Icon }) => (
                    <button
                      type="button"
                      key={label}
                      onClick={() => submitPrompt(prompt, action)}
                      disabled={!context || contextLoading || Boolean(contextError) || sending}
                    >
                      <Icon size={14} aria-hidden="true" />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>
              </details>
            )}
            {messages.length === 0 && (
              <div className="copilot-quick-actions copilot-quick-actions-initial">
                <div className="copilot-action-grid">
                  {QUICK_ACTIONS.map(({ label, prompt, action, icon: Icon }) => (
                    <button
                      type="button"
                      key={label}
                      onClick={() => submitPrompt(prompt, action)}
                      disabled={!context || contextLoading || Boolean(contextError) || sending}
                    >
                      <Icon size={14} aria-hidden="true" />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <form
              className="copilot-composer"
              onSubmit={(event) => {
                event.preventDefault();
                submitPrompt(input);
              }}
            >
              <label className="sr-only" htmlFor="copilot-message">Message Teacher Copilot</label>
              <textarea
                id="copilot-message"
                value={input}
                onChange={(event) => setInputState({ key: contextKey, value: event.target.value })}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    if (canSend) submitPrompt(input);
                  }
                }}
                placeholder={context ? 'Ask about this class…' : 'Select a class to begin'}
                rows={2}
                disabled={!context || contextLoading || Boolean(contextError) || sending}
                aria-describedby="copilot-composer-hint"
              />
              <div className="copilot-composer-footer">
                <span id="copilot-composer-hint">
                  Enter to send · Shift + Enter for a new line
                </span>
                <button type="submit" disabled={!canSend} aria-label="Send message">
                  {sending
                    ? <LoaderCircle size={16} className="copilot-spin" aria-hidden="true" />
                    : <Send size={16} aria-hidden="true" />}
                </button>
              </div>
            </form>
          </>
        ) : (
          <button
            type="button"
            className="copilot-rail-button"
            onClick={() => setIsOpen(true)}
            aria-label="Open Teacher Copilot"
            title="Open Teacher Copilot"
            aria-controls="copilot-title"
          >
            <PanelRightOpen size={18} aria-hidden="true" />
            <span>AI</span>
          </button>
        )}
      </aside>
      {isCompact && !isOpen && (
        <button
          ref={triggerRef}
          type="button"
          className="copilot-mobile-trigger"
          onClick={openPanel}
          aria-label="Open Teacher Copilot"
        >
          <Sparkles size={18} aria-hidden="true" />
          <span>Copilot</span>
        </button>
      )}
    </>
  );
}
