import { useLayoutEffect, useRef } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';
import { useLiteEffects } from '../hooks/useLiteEffects';
import { duration, easing, navigationDirection, routeFrames } from './presets';

export default function RouteTransition({ children }) {
  const location = useLocation();
  const type = useNavigationType();
  const { lite } = useLiteEffects();
  const node = useRef(null);
  const previous = useRef(null);
  const positions = useRef(new Map());
  const lastIndex = useRef(null);
  const motion = useRef(null);
  const liteRef = useRef(lite);
  useLayoutEffect(() => {
    liteRef.current = lite;
  }, [lite]);
  useLayoutEffect(() => {
    const element = node.current;
    const index = window.history.state?.idx ?? 0;
    const direction = navigationDirection(
      previous.current,
      location.pathname,
      type,
      index - (lastIndex.current ?? index),
    );
    previous.current = location.pathname;
    lastIndex.current = index;
    let completed = false;
    const initialFocus = document.activeElement;
    const scrollPositions = positions.current;
    const finish = () => {
      const heading = element?.querySelector('h1');
      if (!heading || !heading.getClientRects().length || completed) return;
      completed = true;
      if (
        document.activeElement === initialFocus ||
        document.activeElement === document.body
      )
        heading.focus({ preventScroll: true });
      const saved = scrollPositions.get(location.key);
      if (location.hash)
        document
          .getElementById(decodeURIComponent(location.hash.slice(1)))
          ?.scrollIntoView();
      else
        window.scrollTo(0, type === 'POP' && saved !== undefined ? saved : 0);
      if (direction !== 'none' && !liteRef.current && element.animate) {
        motion.current?.cancel();
        motion.current = element.animate(routeFrames(direction), {
          duration: duration.page * 1000,
          easing: easing.standard,
        });
      }
    };
    finish();
    const observer = new MutationObserver(finish);
    if (element) observer.observe(element, { childList: true, subtree: true });
    return () => {
      scrollPositions.set(location.key, window.scrollY);
      observer.disconnect();
      motion.current?.cancel();
    };
  }, [location.pathname, location.key, location.hash, type]);
  useLayoutEffect(() => {
    if (lite) motion.current?.cancel();
  }, [lite]);
  return (
    <div className="cp-route-content" ref={node}>
      {children}
    </div>
  );
}
