import LanguageSelector from './LanguageSelector';
import { useI18n } from '../i18n/useI18n';
import { createPortal } from 'react-dom';
import useModalDialog from '../hooks/useModalDialog';
import { useLiteEffects } from '../hooks/useLiteEffects';
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowUpRight,
  BookOpenCheck,
  ChevronDown,
  ChevronRight,
  Clipboard,
  FileText,
  Lightbulb,
  LoaderCircle,
  MessageSquareText,
  PanelRightClose,
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
import { AssistantMessage, ClassContext, UserMessage } from './TeacherCopilotSections';
import './TeacherCopilot.css';

const QUICK_ACTIONS = [
  {
    label: 'Analyze my class',
    prompt:
      'Analyze my class using the current assessment and diagnosis data. Summarize the observed patterns and sample sizes.',
    action: 'summarize_class',
    icon: MessageSquareText,
  },
  {
    label: 'Explain biggest misconception',
    prompt:
      'Explain the most common misconception in this class, using the recorded evidence and a clear teaching response.',
    action: 'summarize_class',
    icon: Lightbulb,
  },
  {
    label: 'Generate a lesson plan',
    prompt:
      'Create a differentiated 45-minute lesson plan for this class and topic.',
    action: 'lesson_plan',
    icon: BookOpenCheck,
  },
  {
    label: 'Create a targeted worksheet',
    prompt:
      'Create a targeted worksheet for this class topic and its most common observed misconception, with answers and explanations.',
    action: 'generate_worksheet',
    icon: FileText,
  },
  {
    label: 'Recommend teaching strategies',
    prompt:
      'Recommend practical, evidence-informed teaching strategies for this class and topic.',
    action: null,
    icon: Lightbulb,
  },
  {
    label: 'Generate practice questions',
    prompt:
      'Generate practice questions for this class topic, including correct answers and explanations.',
    action: 'generate_worksheet',
    icon: Clipboard,
  },
  {
    label: 'Identify students needing attention',
    prompt:
      'Identify students needing attention based on the recorded classroom evidence and explain why.',
    action: 'struggling_students',
    icon: UsersRound,
  },
  {
    label: 'Compare intervention outcomes',
    prompt:
      'Compare intervention and reassessment outcomes for this class, including the sample sizes and observed score change.',
    action: 'compare_outcomes',
    icon: ArrowUpRight,
  },
];

const STARTER_PROMPTS = [
  {
    label: 'What is the class showing?',
    message:
      'Summarize what the current class data shows, including sample sizes and any important limitations.',
    action: 'summarize_class',
  },
  {
    label: 'Plan a focused lesson',
    message:
      'Create a differentiated lesson plan focused on the most important learning need in this class.',
    action: 'lesson_plan',
  },
  {
    label: 'Build a quick check',
    message:
      'Create a short set of practice questions for this topic with answers and explanations.',
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

export default function TeacherCopilot({
  session,
  startSession,
  open,
  onDismiss,
}) {
  const { t } = useI18n();
  const { lite } = useLiteEffects();
  const isOpen = open;
  const isCompact = true;
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
  const panelRef = useModalDialog(open, onDismiss);
  const closeButtonRef = useRef(null);
  const chatRequestId = useRef(0);
  const contextKey = `${session.classId || ''}:${session.subject || ''}:${session.topic || ''}`;
  const contextKeyRef = useRef(contextKey);
  const currentContextState =
    contextState.key === contextKey ? contextState : null;
  const context = currentContextState?.data || null;
  const contextLoading =
    Boolean(session.classId) &&
    (!currentContextState || currentContextState.loading);
  const contextError = session.classId
    ? currentContextState?.error || ''
    : t('Select a class to load its verified classroom context.');
  const currentChat =
    chatState.key === contextKey ? chatState : EMPTY_CHAT_STATE;
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
    () =>
      taxonomy?.[context?.subject]?.find(
        (item) => item.topic === context?.topic,
      ),
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
        if (active)
          setClassesError(getErrorMessage(error, 'Could not load classes.'));
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
        setContextState({
          key: contextKey,
          data: result,
          loading: false,
          error: '',
        });
      })
      .catch((error) => {
        if (active) {
          setContextState({
            key: contextKey,
            data: null,
            loading: false,
            error: getErrorMessage(
              error,
              error.message || 'Could not load this class context.',
            ),
          });
        }
      });
    return () => {
      active = false;
    };
  }, [contextKey, session.classId]);

  useEffect(() => {
    if (open)
      messagesEndRef.current?.scrollIntoView({
        block: 'end',
        behavior: lite ? 'instant' : 'smooth',
      });
  }, [messages, sending, open, lite]);

  function selectClass(classId) {
    const selected = classes.find((item) => item.id === classId);
    if (!selected || selected.id === session.classId || selected.subject !== (session.teachingSubject || session.subject)) return;
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
        .catch((error) =>
          setClassesError(getErrorMessage(error, 'Could not load classes.')),
        )
        .finally(() => setClassesLoading(false));
    }
    if (!session.classId) return;
    setContextState({ key: contextKey, data: null, loading: true, error: '' });
    getCopilotClassContext(session.classId)
      .then((result) => {
        if (result?.class_id !== session.classId) {
          throw new Error('The backend returned a different class context.');
        }
        setContextState({
          key: contextKey,
          data: result,
          loading: false,
          error: '',
        });
      })
      .catch((error) => {
        setContextState({
          key: contextKey,
          data: null,
          loading: false,
          error: getErrorMessage(
            error,
            error.message || 'Could not load this class context.',
          ),
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
      const base =
        current.key === requestKey
          ? current
          : { ...EMPTY_CHAT_STATE, key: requestKey };
      return {
        ...base,
        messages: appendUser
          ? [
              ...base.messages,
              {
                id: `user-${currentId}`,
                role: 'user',
                content: request.message,
              },
            ]
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
      if (
        currentId !== chatRequestId.current ||
        contextKeyRef.current !== requestKey
      )
        return;
      if (
        !response ||
        typeof response.reply !== 'string' ||
        (!response.reply.trim() &&
          !response.draft_content &&
          !response.class_context_summary)
      ) {
        throw new Error(
          'The assistant returned an empty response. Please try again.',
        );
      }
      setChatState((current) =>
        current.key === requestKey
          ? {
              ...current,
              messages: [
                ...current.messages,
                {
                  id: `assistant-${currentId}`,
                  role: 'assistant',
                  response,
                },
              ],
            }
          : current,
      );
    } catch (error) {
      if (
        currentId !== chatRequestId.current ||
        contextKeyRef.current !== requestKey
      )
        return;
      setChatState((current) =>
        current.key === requestKey
          ? {
              ...current,
              error:
                error.message ===
                'The assistant returned an empty response. Please try again.'
                  ? error.message
                  : getErrorMessage(
                      error,
                      'The assistant could not respond. Please try again.',
                    ),
              retryRequest: { ...requestContext },
            }
          : current,
      );
    } finally {
      if (
        currentId === chatRequestId.current &&
        contextKeyRef.current === requestKey
      ) {
        setChatState((current) =>
          current.key === requestKey ? { ...current, sending: false } : current,
        );
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
        content:
          item.role === 'assistant'
            ? item.response?.reply || item.content || ''
            : item.content,
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

  function closePanel() {
    onDismiss();
  }

  const canSend = Boolean(
    context && !contextLoading && !contextError && input.trim() && !sending,
  );

  return createPortal(
    <dialog
      ref={panelRef}
      className={`copilot-panel${isOpen ? ' is-open' : ''}${isCompact ? ' is-compact' : ''}`}
      role={isCompact && isOpen ? 'dialog' : 'complementary'}
      aria-modal={isCompact && isOpen ? 'true' : undefined}
      aria-label={t('Teacher Copilot')}
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
                <h2 id="copilot-title">{t('Teacher Copilot')}</h2>
                <span>{t('Classroom-grounded assistant')}</span>
              </div>
            </div>
            <div className="copilot-header-actions">
              <button
                type="button"
                className="copilot-icon-button"
                onClick={clearConversation}
                disabled={!messages.length || sending}
                aria-label={t('Clear conversation')}
                title={t('Clear conversation')}
              >
                <Trash2 size={16} aria-hidden="true" />
              </button>
              <button
                ref={closeButtonRef}
                type="button"
                className="copilot-icon-button"
                onClick={closePanel}
                aria-label={
                  isCompact
                    ? t('Close Teacher Copilot')
                    : t('Collapse Teacher Copilot')
                }
                title={
                  isCompact ? t('Close assistant') : t('Collapse assistant')
                }
              >
                {isCompact ? (
                  <X size={17} aria-hidden="true" />
                ) : (
                  <PanelRightClose size={17} aria-hidden="true" />
                )}
              </button>
            </div>
          </header>

          <div className="copilot-context-wrap">
            <div className="copilot-language-control">
              <LanguageSelector compact labelKey="Assistant language" />
            </div>
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
                <LoaderCircle
                  size={12}
                  className="copilot-spin"
                  aria-hidden="true"
                />
                {t('Loading classes…')}
              </span>
            )}
          </div>

          <div
            className="copilot-conversation"
            aria-label={t('Copilot conversation')}
          >
            {messages.length === 0 && (
              <section className="copilot-welcome">
                <span className="copilot-welcome-mark" aria-hidden="true">
                  <Sparkles size={18} />
                </span>
                <h3>{t('What would you like to work on?')}</h3>
                <p>
                  {t(
                    'Responses use the selected class context. Generated resources are drafts for your review.',
                  )}
                </p>
                {!contextLoading && !contextError && context && (
                  <div className="copilot-starter-prompts">
                    {starterPrompts.map((prompt) => (
                      <button
                        type="button"
                        key={t(prompt.label)}
                        onClick={() =>
                          submitPrompt(prompt.message, prompt.action)
                        }
                        disabled={!context || sending}
                      >
                        {t(prompt.label)}
                        <ChevronRight size={14} aria-hidden="true" />
                      </button>
                    ))}
                  </div>
                )}
                {contextError && !contextLoading && (
                  <p className="copilot-empty-context">
                    {t(
                      'Load a valid class context to start a grounded conversation.',
                    )}
                  </p>
                )}
              </section>
            )}
            {messages.map((message) =>
              message.role === 'user' ? (
                <UserMessage key={message.id} content={message.content} />
              ) : (
                <AssistantMessage
                  key={message.id}
                  message={message}
                  onFollowup={(prompt) => submitPrompt(prompt)}
                />
              ),
            )}
            {sending && (
              <div className="copilot-loading" role="status" aria-live="polite">
                <span className="copilot-message-avatar" aria-hidden="true">
                  <Sparkles size={14} />
                </span>
                <span className="copilot-loading-dots">
                  <i />
                  <i />
                  <i />
                </span>
                <span>{t('Working with your class context…')}</span>
              </div>
            )}
            {chatError && (
              <div className="copilot-chat-error" role="alert">
                <div>
                  <strong>{t('Couldn’t get a response')}</strong>
                  <p>{chatError}</p>
                </div>
                <button
                  type="button"
                  onClick={retryLastRequest}
                  disabled={!retryRequest || sending}
                >
                  <RefreshCw size={14} aria-hidden="true" />
                  {t('Retry')}
                </button>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {messages.length > 0 && (
            <details className="copilot-quick-actions">
              <summary>
                <span>
                  <Sparkles size={14} aria-hidden="true" /> {t('Quick actions')}
                </span>
                <ChevronDown size={14} aria-hidden="true" />
              </summary>
              <div className="copilot-action-grid">
                {QUICK_ACTIONS.map(({ label, prompt, action, icon: Icon }) => (
                  <button
                    type="button"
                    key={label}
                    onClick={() => submitPrompt(prompt, action)}
                    disabled={
                      !context ||
                      contextLoading ||
                      Boolean(contextError) ||
                      sending
                    }
                  >
                    <Icon size={14} aria-hidden="true" />
                    <span>{t(label)}</span>
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
                    disabled={
                      !context ||
                      contextLoading ||
                      Boolean(contextError) ||
                      sending
                    }
                  >
                    <Icon size={14} aria-hidden="true" />
                    <span>{t(label)}</span>
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
            <label className="sr-only" htmlFor="copilot-message">
              {t('Message Teacher Copilot')}
            </label>
            <textarea
              id="copilot-message"
              value={input}
              onChange={(event) =>
                setInputState({ key: contextKey, value: event.target.value })
              }
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter' &&
                  !event.shiftKey &&
                  !event.nativeEvent.isComposing &&
                  event.keyCode !== 229
                ) {
                  event.preventDefault();
                  if (canSend) submitPrompt(input);
                }
              }}
              placeholder={
                context
                  ? t('Ask about this class…')
                  : t('Select a class to begin')
              }
              rows={2}
              disabled={
                !context || contextLoading || Boolean(contextError) || sending
              }
              aria-describedby="copilot-composer-hint"
            />
            <div className="copilot-composer-footer">
              <span id="copilot-composer-hint">
                {t('Enter to send · Shift + Enter for a new line')}
              </span>
              <button
                type="submit"
                disabled={!canSend}
                aria-label={t('Send message')}
              >
                {sending ? (
                  <LoaderCircle
                    size={16}
                    className="copilot-spin"
                    aria-hidden="true"
                  />
                ) : (
                  <Send size={16} aria-hidden="true" />
                )}
              </button>
            </div>
          </form>
        </>
      ) : null}
    </dialog>,
    document.body,
  );
}
