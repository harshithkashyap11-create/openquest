import { useRef, useState } from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { useI18n } from '../../i18n/useI18n';
import QuestionTransition from '../../motion/QuestionTransition';
import ProgressBar from './ProgressBar';
import Button from './Button';
export default function QuestionPager({
  questions,
  busy,
  submitLabel,
  children,
}) {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState('forward');
  const content = useRef(null);
  const { t } = useI18n();
  const current = Math.min(index, questions.length - 1);
  const question = questions[current];
  if (!question) return null;
  function move(delta) {
    if (busy) return;
    if (delta > 0) {
      const invalid = [
        ...content.current.querySelectorAll('input,textarea,select'),
      ].find((field) => !field.checkValidity());
      if (invalid) {
        invalid.reportValidity();
        return;
      }
    }
    setDirection(delta > 0 ? 'forward' : 'backward');
    setIndex(current + delta);
  }
  return (
    <div className="cp-question-pager">
      <div className="assessment-progress">
        <span>
          {t('questionPosition', {
            current: current + 1,
            total: questions.length,
          })}
        </span>
        <span>{t('answersStayHere')}</span>
      </div>
      <ProgressBar
        value={current + 1}
        max={questions.length}
        label={t('questionProgress')}
      />
      <div
        ref={content}
        onKeyDown={(event) => {
          if (
            event.key === 'Enter' &&
            event.target.tagName === 'INPUT' &&
            current < questions.length - 1 &&
            !event.nativeEvent.isComposing
          ) {
            event.preventDefault();
            move(1);
          }
        }}
      >
        <QuestionTransition
          questionId={question.id ?? question.question_index}
          direction={direction}
        >
          {children(question, current)}
        </QuestionTransition>
      </div>
      <div className="cp-question-actions">
        <Button
          variant="secondary"
          disabled={busy || current === 0}
          onClick={() => move(-1)}
        >
          <ArrowLeft size={16} aria-hidden="true" />
          {t('previousQuestion')}
        </Button>
        {current < questions.length - 1 ? (
          <Button disabled={busy} onClick={() => move(1)}>
            {t('nextQuestion')}
            <ArrowRight size={16} aria-hidden="true" />
          </Button>
        ) : submitLabel ? (
          <Button type="submit" busy={busy}>
            {submitLabel}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
