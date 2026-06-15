import { useCallback, useEffect, useRef, useState } from 'react';

import { apiClient } from '../../services/apiClient';

const POLL_INTERVAL_MS = 30_000; // poll every 30s
const isTestEnvironment = typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test';
const PRIORITY_COLORS = {
  urgente: 'var(--danger)',
  alta: 'var(--warning)',
  normal: 'var(--brand)',
  baja: 'var(--muted)',
};

const TIPO_ICONS = {
  calificacion: '📝',
  asistencia: '📋',
  evaluacion: '📊',
  alerta: '⚠️',
  sistema: '⚙️',
  tarea_nueva: '📚',
  tarea_entregada: '✅',
  tarea_calificada: '🎯',
  anuncio_nuevo: '📢',
  mensaje_nuevo: '💬',
  comunicado_nuevo: '📨',
  evento_nuevo: '📅',
  citacion_nueva: '🔔',
  noticia_nueva: '📰',
  urgente_nuevo: '🚨',
};

function timeAgo(isoDate) {
  const now = new Date();
  const date = new Date(isoDate);
  const diffMs = now - date;
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return 'ahora';
  if (minutes < 60) return `hace ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days}d`;
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef(null);

  // Fetch summary (unread count) on mount + interval
  const fetchSummary = useCallback(async () => {
    try {
      const data = await apiClient.get('/api/v1/notificaciones/resumen/');
      setUnreadCount(data.unread_count ?? 0);
    } catch {
      // silent fail - non-critical
    }
  }, []);

  // Fetch full notification list
  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.get('/api/v1/notificaciones/?limit=30');
      setNotifications(Array.isArray(data) ? data : []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll summary
  useEffect(() => {
    fetchSummary();
    if (isTestEnvironment) {
      return undefined;
    }

    const id = setInterval(fetchSummary, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchSummary]);

  function handleToggle() {
    setOpen((prev) => {
      const next = !prev;
      if (next) {
        fetchNotifications();
      }
      return next;
    });
  }

  // Close on click outside
  useEffect(() => {
    function onClickOutside(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener('mousedown', onClickOutside);
    }
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [open]);

  async function markRead(notifId) {
    try {
      await apiClient.post(`/api/v1/notificaciones/${notifId}/marcar-leida/`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notifId ? { ...n, leido: true } : n)),
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // silent
    }
  }

  async function markAllRead() {
    try {
      await apiClient.post('/api/v1/notificaciones/marcar-todas-leidas/');
      setNotifications((prev) => prev.map((n) => ({ ...n, leido: true })));
      setUnreadCount(0);
    } catch {
      // silent
    }
  }

  return (
    <div className="notif-bell-wrapper" ref={panelRef}>
      <button
        type="button"
        className="notif-bell-btn"
        onClick={handleToggle}
        aria-label={`Notificaciones (${unreadCount} sin leer)`}
      >
        <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
          <path d="M12 2C10.34 2 9 3.34 9 5v.29C6.12 6.43 4 9.02 4 12v5l-2 2v1h20v-1l-2-2v-5c0-2.98-2.12-5.57-5-6.71V5c0-1.66-1.34-3-3-3zm0 20c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2z" />
        </svg>
        {unreadCount > 0 ? (
          <span className="notif-bell-badge">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="notif-panel">
          <div className="notif-panel-header">
            <h3>Notificaciones</h3>
            {unreadCount > 0 ? (
              <button
                type="button"
                className="notif-mark-all"
                onClick={markAllRead}
              >
                Marcar todas leídas
              </button>
            ) : null}
          </div>

          <div className="notif-panel-body">
            {loading ? (
              <div className="notif-loading">
                <div className="loading-dot" role="status" aria-live="polite" aria-label="Cargando"><span /><span /><span /></div>
              </div>
            ) : notifications.length === 0 ? (
              <p className="notif-empty">Sin notificaciones</p>
            ) : (
              notifications.map((n) => (
                <button
                  type="button"
                  key={n.id}
                  className={`notif-item ${n.leido ? 'read' : 'unread'}`}
                  onClick={() => !n.leido && markRead(n.id)}
                >
                  <span className="notif-item-icon">
                    {TIPO_ICONS[n.tipo] || '🔔'}
                  </span>
                  <div className="notif-item-content">
                    <span className="notif-item-title">{n.titulo}</span>
                    <span className="notif-item-msg">{n.mensaje}</span>
                    <span className="notif-item-meta">
                      <span
                        className="notif-priority-dot"
                        style={{ background: PRIORITY_COLORS[n.prioridad] || PRIORITY_COLORS.normal }}
                      />
                      {timeAgo(n.fecha_creacion)}
                    </span>
                  </div>
                  {!n.leido ? <span className="notif-unread-dot" /> : null}
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}


