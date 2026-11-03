import { useLayoutEffect, useRef } from 'react';

// Native showModal supplies focus containment, background inertness and top-layer stacking.
export default function useModalDialog(open, onClose) {
  const ref = useRef(null);
  const closeRef = useRef(onClose);
  useLayoutEffect(() => {
    closeRef.current = onClose;
  }, [onClose]);
  useLayoutEffect(() => {
    const dialog = ref.current;
    if (!open || !dialog) return;
    const opener = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    if (!dialog.open) dialog.showModal();
    const cancel = (event) => {
      event.preventDefault();
      closeRef.current();
    };
    const trap = (event) => {
      if (event.key !== 'Tab') return;
      const controls = [
        ...dialog.querySelectorAll(
          'a[href],button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),summary,[tabindex="0"]',
        ),
      ].filter((el) => el.getClientRects().length);
      const first = controls[0],
        last = controls.at(-1);
      if (!first) {
        event.preventDefault();
        dialog.focus();
      } else if (
        event.shiftKey &&
        (document.activeElement === first || document.activeElement === dialog)
      ) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    dialog.addEventListener('cancel', cancel);
    dialog.addEventListener('keydown', trap);
    return () => {
      dialog.removeEventListener('cancel', cancel);
      dialog.removeEventListener('keydown', trap);
      dialog.close();
      document.body.style.overflow = overflow;
      if (opener?.isConnected && !document.querySelector('dialog[open]'))
        opener.focus({ preventScroll: true });
    };
  }, [open]);
  return ref;
}
