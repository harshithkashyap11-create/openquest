import { useLayoutEffect, useRef } from 'react';
import { useLiteEffects } from '../hooks/useLiteEffects';
import { duration, easing, routeFrames } from './presets';
export default function QuestionTransition({
  questionId,
  direction = 'forward',
  children,
}) {
  const node = useRef(null);
  const previous = useRef(questionId);
  const { lite } = useLiteEffects();
  useLayoutEffect(() => {
    if (previous.current === questionId) return;
    previous.current = questionId;
    node.current
      ?.querySelector('[data-question-heading]')
      ?.focus({ preventScroll: true });
    if (lite || !node.current?.animate) return;
    const animation = node.current.animate(routeFrames(direction), {
      duration: duration.page * 1000,
      easing: easing.standard,
    });
    return () => animation.cancel();
  }, [questionId, direction, lite]);
  return (
    <div ref={node} className="cp-question-transition">
      {children}
    </div>
  );
}
