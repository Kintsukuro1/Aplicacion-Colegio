import { useNotificationStore } from '../../stores/useNotificationStore';

/**
 * Sistema de notificaciones toast minimalista.
 *
 * Uso:
 *   import { ToastProvider, useToast } from './Toast';
 *
 *   // En App root:
 *   <ToastProvider><App /></ToastProvider>
 *
 *   // En cualquier componente:
 *   const toast = useToast();
 *   toast.success('Guardado correctamente');
 *   toast.error('No se pudo eliminar');
 *   toast.info('Datos actualizados');
 */

export function ToastProvider({ children }) {
  const toasts = useNotificationStore((state) => state.toasts);
  const dismiss = useNotificationStore((state) => state.dismiss);

  return (
    <>
      {children}
      <div className="toast-container" aria-live="polite" aria-atomic="true">
        {toasts.map((t) => {
          const isAlert = t.type === 'error' || t.type === 'warning';
          const role = isAlert ? 'alert' : 'status';
          const live = isAlert ? 'assertive' : 'polite';

          return (
            <div
              key={t.id}
              className={`toast toast-${t.type}`}
              role={role}
              aria-live={live}
              aria-atomic="true"
            >
            <span className="toast-icon">
              {t.type === 'success' && 'OK'}
              {t.type === 'error' && 'X'}
              {t.type === 'info' && 'i'}
              {t.type === 'warning' && '!'}
            </span>
            <span className="toast-message">{t.message}</span>
            <button
              type="button"
              className="toast-dismiss"
              onClick={() => dismiss(t.id)}
              aria-label="Cerrar"
            >
              X
            </button>
            </div>
          );
        })}
      </div>
    </>
  );
}

export function useToast() {
  // We can just return the store directly since it has the methods
  return useNotificationStore();
}
