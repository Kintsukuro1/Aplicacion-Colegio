import { useEffect, useId, useRef } from 'react';

export default function FormOverlay({ isOpen, onClose, title, children }) {
  const dialogId = useId();
  const bodyId = useId();
  const overlayRef = useRef(null);
  const lastFocusedRef = useRef(null);
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const overlayEl = overlayRef.current;
    if (!overlayEl) {
      return;
    }

    lastFocusedRef.current = document.activeElement;

    const focusableSelector =
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const focusables = Array.from(overlayEl.querySelectorAll(focusableSelector)).filter(
      (el) => !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden')
    );
    const initialFocus = focusables[0] || overlayEl;

    if (initialFocus === overlayEl) {
      overlayEl.setAttribute('tabindex', '-1');
    }
    initialFocus.focus();

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose();
        return;
      }

      if (event.key !== 'Tab') {
        return;
      }

      const currentFocusables = Array.from(
        overlayEl.querySelectorAll(focusableSelector)
      ).filter((el) => !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden'));
      if (currentFocusables.length === 0) {
        event.preventDefault();
        overlayEl.focus();
        return;
      }

      const first = currentFocusables[0];
      const last = currentFocusables[currentFocusables.length - 1];
      const isShift = event.shiftKey;
      const active = document.activeElement;

      if (!isShift && active === last) {
        event.preventDefault();
        first.focus();
      } else if (isShift && active === first) {
        event.preventDefault();
        last.focus();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (lastFocusedRef.current && typeof lastFocusedRef.current.focus === 'function') {
        lastFocusedRef.current.focus();
      }
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  function handleBackdropKeyDown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onClose();
    }
  }

  return (
    <div
      className="form-overlay-backdrop"
      onPointerDown={onClose}
      onKeyDown={handleBackdropKeyDown}
      role="button"
      tabIndex={0}
      aria-label="Cerrar dialogo"
    >
      <div
        ref={overlayRef}
        className="card form-overlay-content"
        role="dialog"
        aria-modal="true"
        aria-labelledby={dialogId}
        aria-describedby={bodyId}
        onPointerDown={(e) => e.stopPropagation()}
      >
        <header className="form-overlay-header">
          <h3 id={dialogId}>{title}</h3>
          <button type="button" className="small secondary" onClick={onClose} aria-label="Cerrar">
            X
          </button>
        </header>
        <div className="form-overlay-body" id={bodyId}>
          {children}
        </div>
      </div>
    </div>
  );
}
