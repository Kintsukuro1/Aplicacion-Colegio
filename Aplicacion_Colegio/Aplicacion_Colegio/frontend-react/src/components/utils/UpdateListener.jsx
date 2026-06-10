import { useCallback, useEffect, useRef, useState } from 'react';
import { useToast } from '../feedback/Toast';

/**
 * UpdateListener
 *
 * Escucha mensajes de actualización del Service Worker y muestra notificaciones
 * al usuario cuando hay una nueva versión disponible.
 *
 * Proporciona:
 * - Notificación inmediata de nueva versión
 * - Botón "Recargar ahora" para aplicar cambios inmediatamente
 * - Auto-reload después de 10 minutos si no se interactúa
 */
export function UpdateListener() {
  const toast = useToast();
  const [updateState, setUpdateState] = useState({
    available: false,
    version: '',
  });
  const updatePromptRef = useRef(null);
  const reloadTimerRef = useRef(null);
  const lastVersionRef = useRef('');
  const { available: updateAvailable, version: updateVersion } = updateState;

  const performReload = useCallback(async () => {
    setUpdateState((current) => ({ ...current, available: false }));
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      window.location.reload();
      return;
    }

    let controllerChanged = false;
    const handleControllerChange = () => {
      if (controllerChanged) {
        return;
      }
      controllerChanged = true;
      window.location.reload();
    };

    navigator.serviceWorker.addEventListener('controllerchange', handleControllerChange);

    try {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration?.waiting) {
        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
    } finally {
      setTimeout(() => {
        navigator.serviceWorker.removeEventListener('controllerchange', handleControllerChange);
        if (!controllerChanged) {
          window.location.reload();
        }
      }, 5000);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    const handleUpdateMessage = (event) => {
      if (event.data?.type === 'SW_UPDATE_AVAILABLE') {
        const version = event.data.version;
        if (version && lastVersionRef.current === version) {
          return;
        }
        console.log('[PWA] New version available:', version);

        // Store update info
        updatePromptRef.current = {
          version,
          timestamp: Date.now(),
        };

        lastVersionRef.current = version || '';

        setUpdateState({ available: true, version: version || '' });

        // Show toast with action button (reload now)
        // Toast with duration 0 means it won't auto-dismiss
        toast.info(
          `Nueva version disponible${version ? ` (${version})` : ''}. Auto reload en 10 minutos.`,
          0
        );

        // Auto-reload after 10 minutes if user hasn't reloaded manually
        reloadTimerRef.current = setTimeout(() => {
          if (updatePromptRef.current && Date.now() - updatePromptRef.current.timestamp > 600000) {
            console.log('[PWA] Auto-reloading to apply new version...');
            performReload();
          }
        }, 600000);
      }
    };

    // Expose reload function globally for testing/manual triggering
    window.__updateApp = performReload;

    navigator.serviceWorker.addEventListener('message', handleUpdateMessage);

    return () => {
      clearTimeout(reloadTimerRef.current);
      navigator.serviceWorker.removeEventListener('message', handleUpdateMessage);
      delete window.__updateApp;
    };
  }, [performReload, toast]);

  return updateAvailable ? (
    <div className="update-banner" role="status" aria-live="polite">
      <span>
        Nueva version disponible{updateVersion ? ` (${updateVersion})` : ''}.
      </span>
      <div className="update-banner-actions">
        <button type="button" className="secondary" onClick={performReload}>
          Recargar
        </button>
        <button
          type="button"
          className="small"
          onClick={() => setUpdateState((current) => ({ ...current, available: false }))}
        >
          Despues
        </button>
      </div>
    </div>
  ) : null;
}

