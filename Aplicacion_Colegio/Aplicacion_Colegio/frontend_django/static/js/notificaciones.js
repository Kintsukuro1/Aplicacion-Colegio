/**
 * Campana de notificaciones del dashboard (profesor, estudiante, apoderado, admin).
 * - Lista y badge vía API REST
 * - Tiempo real vía SSE (/api/v1/notificaciones/stream/)
 * - Fallback: polling cada 30s si SSE no está disponible
 */
document.addEventListener('DOMContentLoaded', () => {
    if (window.__colegioNotifInit) {
        return;
    }

    function isVisible(el) {
        if (!el || !el.isConnected) return false;
        let node = el;
        while (node) {
            const style = window.getComputedStyle(node);
            if (style.display === 'none' || style.visibility === 'hidden') {
                return false;
            }
            node = node.parentElement;
        }
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    const container = Array.from(document.querySelectorAll('.notificaciones-container')).find(isVisible)
        || document.querySelector('.notificaciones-container');
    const btn = container?.querySelector('#btnNotificaciones');
    const dropdown = container?.querySelector('#dropdownNotificaciones');
    const list = container?.querySelector('#listNotificaciones');
    const badge = container?.querySelector('#badgeNotificaciones');
    const btnMarkAll = container?.querySelector('#btnMarcarTodas');

    if (!container || !btn || !dropdown || !list || !badge || !btnMarkAll) {
        return;
    }

    window.__colegioNotifInit = true;

    const API = {
        summary: '/api/v1/notificaciones/resumen/',
        list: '/api/v1/notificaciones/?limit=30',
        stream: '/api/v1/notificaciones/stream/',
        markAll: '/api/v1/notificaciones/marcar-todas-leidas/',
        markOne: (id) => `/api/v1/notificaciones/${id}/marcar-leida/`,
    };

    const POLL_MS = 30000;
    const REQUEST_TIMEOUT_MS = 10000;
    const SSE_RECONNECT_MS = 4000;
    const TOAST_DURATION_MS = 6000;
    const MAX_TOASTS = 4;
    const STORAGE_KEY = 'colegio_notif_last_id';

    let notifications = [];
    let unreadCount = 0;
    let loading = false;
    let lastStreamId = 0;
    let eventSource = null;
    let sseFailures = 0;
    let pollTimer = null;
    let toastStack = null;

    function isValidCsrfToken(token) {
        if (!token) return false;
        const cleaned = String(token).trim();
        if (cleaned === 'NOTPROVIDED') return false;
        return /^[A-Za-z0-9]{32}$/.test(cleaned) || /^[A-Za-z0-9]{64}$/.test(cleaned);
    }

    function getCsrfToken() {
        const templateToken = container.dataset.csrfToken;
        if (isValidCsrfToken(templateToken)) return String(templateToken).trim();

        const cookieMatch = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (cookieMatch && cookieMatch[1]) {
            const cookieToken = decodeURIComponent(cookieMatch[1]);
            if (isValidCsrfToken(cookieToken)) return cookieToken;
        }

        const inputToken = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (inputToken && isValidCsrfToken(inputToken.value)) return String(inputToken.value).trim();

        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            const content = metaToken.getAttribute('content');
            if (isValidCsrfToken(content)) return String(content).trim();
        }
        return '';
    }

    function escapeHtml(text) {
        return String(text || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function timeAgo(isoDate) {
        const now = new Date();
        const date = new Date(isoDate);
        const diffMs = now - date;
        const minutes = Math.floor(diffMs / 60000);
        if (!Number.isFinite(minutes) || minutes < 1) return 'ahora';
        if (minutes < 60) return `hace ${minutes}m`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `hace ${hours}h`;
        const days = Math.floor(hours / 24);
        return `hace ${days}d`;
    }

    function getPortalRole() {
        const body = document.body;
        if (body.classList.contains('vista-apoderado')) return 'apoderado';
        if (body.classList.contains('vista-alumno') || body.classList.contains('perfil-alumno')) {
            return 'estudiante';
        }
        if (body.classList.contains('vista-personal') || body.classList.contains('perfil-personal')) {
            return 'profesor';
        }
        return 'default';
    }

    function resolveDefaultNotificationLink(tipo) {
        const role = getPortalRole();
        const maps = {
            apoderado: {
                calificacion: '/dashboard/?pagina=notas',
                asistencia: '/dashboard/?pagina=asistencia',
                alerta: '/dashboard/?pagina=notas',
                comunicado_nuevo: '/comunicados/',
                citacion_nueva: '/dashboard/?pagina=calendario_pupilo',
                mensaje_nuevo: '/mensajeria/bandeja/',
                mensaje: '/mensajeria/bandeja/',
                default: '/dashboard/?pagina=inicio',
            },
            estudiante: {
                calificacion: '/dashboard/?pagina=mis_notas',
                asistencia: '/dashboard/?pagina=asistencia',
                evaluacion: '/dashboard/?pagina=mis_evaluaciones',
                tarea_nueva: '/dashboard/?pagina=mis_tareas',
                tarea_calificada: '/dashboard/?pagina=mis_tareas',
                comunicado_nuevo: '/comunicados/',
                mensaje_nuevo: '/mensajeria/bandeja/',
                default: '/dashboard/?pagina=inicio',
            },
            profesor: {
                calificacion: '/dashboard/?pagina=notas',
                asistencia: '/dashboard/?pagina=asistencia',
                evaluacion: '/dashboard/?pagina=notas',
                tarea_entregada: '/dashboard/?pagina=tareas_consolidado',
                tarea_nueva: '/dashboard/?pagina=notas',
                sistema: '/dashboard/?pagina=inicio',
                default: '/dashboard/?pagina=inicio',
            },
            default: {
                default: '/dashboard/?pagina=notificaciones',
            },
        };
        const roleMap = maps[role] || maps.default;
        return roleMap[tipo] || roleMap.default;
    }

    function normalizeEstudianteClaseDashboardLink(link) {
        if (!link.startsWith('/dashboard/?pagina=clase')) return link;
        try {
            const search = link.split('?')[1] || '';
            const params = new URLSearchParams(search);
            const claseId = params.get('id');
            if (!claseId) return '/dashboard/?pagina=mis_clases';
            params.delete('pagina');
            params.delete('id');
            const rest = params.toString();
            return rest ? `/estudiante/clase/${claseId}/?${rest}` : `/estudiante/clase/${claseId}/`;
        } catch (_error) {
            return '/dashboard/?pagina=mis_clases';
        }
    }

    function normalizeEstudianteClasePathForProfesor(link) {
        const withQuery = link.match(/^\/estudiante\/clase\/(\d+)\/?\?(.*)$/);
        if (withQuery) {
            const [, claseId, query] = withQuery;
            return `/dashboard/?pagina=clase&id=${claseId}&${query}`;
        }
        const plain = link.match(/^\/estudiante\/clase\/(\d+)\/?$/);
        if (plain) {
            return `/dashboard/?pagina=clase&id=${plain[1]}`;
        }
        const ampQuery = link.match(/^\/estudiante\/clase\/(\d+)\/(.*)$/);
        if (ampQuery) {
            const [, claseId, suffix] = ampQuery;
            const query = suffix.startsWith('?') ? suffix.slice(1) : suffix.startsWith('&') ? suffix.slice(1) : suffix;
            return query
                ? `/dashboard/?pagina=clase&id=${claseId}&${query}`
                : `/dashboard/?pagina=clase&id=${claseId}`;
        }
        return link;
    }

    function isMensajeriaDashboardLink(href) {
        if (!href || href.indexOf('/dashboard') !== 0) return false;
        if (/pagina=mensaje/i.test(href)) return true;
        try {
            const qs = new URL(href, window.location.origin).searchParams;
            const pagina = (qs.get('pagina') || '').toLowerCase();
            return pagina === 'mensajes' || pagina === 'mensajeria' || pagina.indexOf('mensaj') === 0;
        } catch (_e) {
            return /pagina=mensaje/i.test(href);
        }
    }

    function resolveMensajeriaFromDashboard(href) {
        try {
            const qs = new URL(href, window.location.origin).searchParams;
            const convId = qs.get('conversacion_id') || qs.get('id_conversacion') || qs.get('id');
            if (convId && /^\d+$/.test(convId)) {
                return '/mensajeria/conversacion/' + convId + '/';
            }
        } catch (_e) { /* ignore */ }
        return '/mensajeria/bandeja/';
    }

    function normalizeMensajeriaNotificationLink(link, tipo) {
        const t = (tipo || '').toLowerCase();
        const href = String(link || '').trim();
        const isMensaje = t === 'mensaje_nuevo' || t === 'mensaje';

        const convMatch = href.match(/^\/mensajeria\/conversacion\/(\d+)\/?/i);
        if (convMatch) {
            return '/mensajeria/conversacion/' + convMatch[1] + '/';
        }

        if (isMensajeriaDashboardLink(href)) {
            return resolveMensajeriaFromDashboard(href);
        }

        if (
            isMensaje
            || /pagina=mensaje/i.test(href)
            || /^\/mensajeria\/?$/.test(href)
            || href === '/mensajeria/mensajes/'
            || (href.indexOf('/mensajeria') === 0 && href.indexOf('conversacion') === -1)
        ) {
            if (!href || href === '#' || isMensajeriaDashboardLink(href) || /^\/mensajeria\/?$/.test(href)) {
                return '/mensajeria/bandeja/';
            }
        }

        return href;
    }

    function normalizeNotificationLink(rawLink, notification) {
        const tipo = (notification && notification.tipo) || '';
        let link = String(rawLink || '').trim();
        const role = getPortalRole();

        if (!link) {
            return resolveDefaultNotificationLink(tipo);
        }

        link = normalizeMensajeriaNotificationLink(link, tipo);
        if (!link) {
            return resolveDefaultNotificationLink(tipo);
        }

        const apoderadoLegacy = link.match(/^\/apoderado\/estudiante\/(\d+)\/(asistencia|notas)\/?$/);
        if (apoderadoLegacy) {
            const pagina = apoderadoLegacy[2] === 'asistencia' ? 'asistencia' : 'notas';
            return `/dashboard/?pagina=${pagina}&estudiante_id=${apoderadoLegacy[1]}`;
        }

        if (/^\/apoderado\/panel\/?$/.test(link)) {
            return '/dashboard/?pagina=inicio';
        }

        if (/^\/profesor\/evaluaciones\/?/.test(link)) {
            return '/dashboard/?pagina=notas';
        }

        if (/^\/profesor\/asistencias?\/?/.test(link)) {
            return '/dashboard/?pagina=asistencia';
        }

        if (link === '/estudiante/panel' || link.startsWith('/estudiante/panel/')) {
            return '/dashboard/?pagina=inicio';
        }

        if (link.startsWith('/estudiante/clase/') && role === 'profesor') {
            return normalizeEstudianteClasePathForProfesor(link);
        }

        if (link.startsWith('/dashboard/?pagina=clase') && role === 'estudiante') {
            return normalizeEstudianteClaseDashboardLink(link);
        }

        if (link.startsWith('/dashboard/?pagina=clase') && role !== 'estudiante') {
            return link;
        }

        return link;
    }

    function tipoIcon(tipo) {
        const icons = {
            calificacion: '⭐',
            asistencia: '📋',
            evaluacion: '📊',
            alerta: '⚠️',
            tarea_nueva: '📝',
            tarea_entregada: '📤',
            comunicado: '📢',
            mensaje_nuevo: '💬',
            mensaje: '💬',
            sistema: '🔔',
        };
        return icons[tipo] || '🔔';
    }

    async function apiRequest(path, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
        const headers = { Accept: 'application/json', ...(options.headers || {}) };

        if (options.method && options.method !== 'GET') {
            const csrfToken = getCsrfToken();
            if (csrfToken) headers['X-CSRFToken'] = csrfToken;
            headers['Content-Type'] = 'application/json';
        }

        try {
            const response = await fetch(path, {
                ...options,
                credentials: 'same-origin',
                headers,
                signal: controller.signal,
            });
            let payload = null;
            try {
                payload = await response.json();
            } catch (_error) {
                payload = null;
            }
            if (!response.ok) {
                const detail = payload && payload.detail ? payload.detail : `HTTP ${response.status}`;
                throw new Error(detail);
            }
            return payload;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    function persistLastId() {
        try {
            localStorage.setItem(STORAGE_KEY, String(lastStreamId));
        } catch (_e) {
            /* ignore */
        }
    }

    function loadLastId() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            const parsed = parseInt(raw || '0', 10);
            if (Number.isFinite(parsed) && parsed >= 0) lastStreamId = parsed;
        } catch (_e) {
            lastStreamId = 0;
        }
    }

    function setLoadingState() {
        loading = true;
        list.innerHTML = '<div class="notif-loading">Cargando...</div>';
    }

    function setErrorState(message) {
        loading = false;
        list.innerHTML = `<div class="notif-empty">${escapeHtml(message)}</div>`;
    }

    function renderBadge() {
        if (unreadCount > 0) {
            badge.classList.remove('d-none');
            badge.textContent = unreadCount > 99 ? '99+' : String(unreadCount);
        } else {
            badge.classList.add('d-none');
            badge.textContent = '0';
        }
    }

    function renderList() {
        loading = false;
        if (!Array.isArray(notifications) || notifications.length === 0) {
            list.innerHTML = '<div class="notif-empty">Sin notificaciones</div>';
            return;
        }

        list.innerHTML = notifications
            .map((n) => {
                const title = escapeHtml(n.titulo || 'Notificación');
                const message = escapeHtml(n.mensaje || '');
                const unreadClass = n.leido ? '' : ' notif-no-leida';
                const meta = timeAgo(n.fecha_creacion);
                const normalizedLink = normalizeNotificationLink(n.enlace, n);
                return `
                    <a href="${escapeHtml(normalizedLink)}" class="notif-item${unreadClass}" data-id="${n.id}">
                        <div class="notif-item-content">
                            <div class="notif-item-title">${title}</div>
                            <div class="notif-item-message">${message}</div>
                            <div class="notif-item-meta">${meta}</div>
                        </div>
                    </a>
                `;
            })
            .join('');
    }

    function ensureToastStack() {
        if (toastStack) return toastStack;
        toastStack = document.createElement('div');
        toastStack.className = 'notif-toast-stack';
        toastStack.setAttribute('aria-live', 'polite');
        document.body.appendChild(toastStack);
        return toastStack;
    }

    function showToast(notification) {
        const stack = ensureToastStack();
        const prioridad = notification.prioridad || 'normal';
        const toastClass =
            prioridad === 'urgente' ? ' notif-toast--urgente' : prioridad === 'alta' ? ' notif-toast--alta' : '';
        const link = normalizeNotificationLink(notification.enlace, notification);
        const toast = document.createElement('a');
        toast.href = link;
        toast.className = `notif-toast${toastClass}`;
        toast.innerHTML = `
            <span class="notif-toast__icon" aria-hidden="true">${tipoIcon(notification.tipo)}</span>
            <div class="notif-toast__body">
                <p class="notif-toast__title">${escapeHtml(notification.titulo || 'Nueva notificación')}</p>
                <p class="notif-toast__msg">${escapeHtml(notification.mensaje || '')}</p>
            </div>
            <button type="button" class="notif-toast__close" aria-label="Cerrar">×</button>
        `;

        const closeBtn = toast.querySelector('.notif-toast__close');
        closeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toast.remove();
        });

        toast.addEventListener('click', (e) => {
            if (e.target === closeBtn) return;
            if (notification.id && !notification.leido) {
                markNotificationRead(notification.id);
            }
        });

        stack.prepend(toast);
        while (stack.children.length > MAX_TOASTS) {
            stack.lastElementChild.remove();
        }

        window.setTimeout(() => {
            if (toast.isConnected) toast.remove();
        }, TOAST_DURATION_MS);
    }

    function upsertNotification(incoming) {
        if (!incoming || !incoming.id) return;

        const exists = notifications.find((n) => n.id === incoming.id);
        if (exists) {
            notifications = notifications.map((n) => (n.id === incoming.id ? { ...n, ...incoming } : n));
        } else {
            notifications = [incoming, ...notifications].slice(0, 30);
            if (!incoming.leido) {
                unreadCount += 1;
                showToast(incoming);
            }
        }

        if (incoming.id > lastStreamId) {
            lastStreamId = incoming.id;
            persistLastId();
        }

        renderBadge();
        if (isOpen()) renderList();
    }

    async function fetchSummary() {
        try {
            const data = await apiRequest(API.summary);
            unreadCount = Number(data && data.unread_count ? data.unread_count : 0);
            renderBadge();
        } catch (_error) {
            /* non-critical */
        }
    }

    async function fetchNotifications() {
        setLoadingState();
        try {
            const data = await apiRequest(API.list);
            notifications = Array.isArray(data) ? data : [];
            unreadCount = notifications.filter((n) => !n.leido).length;
            const maxId = notifications.reduce((m, n) => Math.max(m, n.id || 0), 0);
            if (maxId > lastStreamId) {
                lastStreamId = maxId;
                persistLastId();
            }
            renderBadge();
            renderList();
        } catch (error) {
            setErrorState('No se pudieron cargar las notificaciones.');
            console.error('[Notificaciones] Error al cargar lista:', error);
        }
    }

    function handleStreamNotification(data) {
        upsertNotification(data);
    }

    function stopSSE() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    }

    function startSSE() {
        if (typeof EventSource === 'undefined') {
            startPollingOnly();
            return;
        }

        stopSSE();
        const url = `${API.stream}?last_id=${lastStreamId}`;
        eventSource = new EventSource(url);

        eventSource.addEventListener('notification', (event) => {
            sseFailures = 0;
            try {
                const data = JSON.parse(event.data);
                if (event.lastEventId) {
                    const parsed = parseInt(event.lastEventId, 10);
                    if (Number.isFinite(parsed)) lastStreamId = Math.max(lastStreamId, parsed);
                }
                handleStreamNotification(data);
            } catch (err) {
                console.error('[Notificaciones] SSE parse error:', err);
            }
        });

        eventSource.addEventListener('keepalive', () => {
            sseFailures = 0;
        });

        eventSource.onopen = () => {
            sseFailures = 0;
        };

        eventSource.onerror = () => {
            sseFailures += 1;
            stopSSE();
            if (sseFailures >= 3) {
                startPollingOnly();
                return;
            }
            window.setTimeout(startSSE, SSE_RECONNECT_MS);
        };
    }

    function startPollingOnly() {
        if (pollTimer) return;
        fetchSummary();
        pollTimer = window.setInterval(() => {
            fetchSummary();
            if (isOpen() && !loading) fetchNotifications();
        }, POLL_MS);
    }

    function startRealtime() {
        loadLastId();
        fetchSummary();
        startSSE();
        window.setInterval(fetchSummary, POLL_MS);
    }

    async function markNotificationRead(notificationId) {
        try {
            await apiRequest(API.markOne(notificationId), { method: 'POST', body: '{}' });
            notifications = notifications.map((n) => (n.id === notificationId ? { ...n, leido: true } : n));
            unreadCount = notifications.filter((n) => !n.leido).length;
            renderBadge();
            renderList();
        } catch (error) {
            console.error('[Notificaciones] Error al marcar notificacion:', error);
        }
    }

    async function markAllRead() {
        try {
            await apiRequest(API.markAll, { method: 'POST', body: '{}' });
            notifications = notifications.map((n) => ({ ...n, leido: true }));
            unreadCount = 0;
            renderBadge();
            renderList();
        } catch (error) {
            console.error('[Notificaciones] Error al marcar todas:', error);
        }
    }

    const isOpen = () => !dropdown.classList.contains('d-none');

    const open = () => {
        dropdown.classList.remove('d-none');
        fetchNotifications();
    };

    const close = () => {
        dropdown.classList.add('d-none');
    };

    const toggle = () => {
        if (isOpen()) close();
        else open();
    };

    if (!dropdown.classList.contains('d-none')) {
        dropdown.classList.add('d-none');
    }

    btn.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        toggle();
    });

    btnMarkAll.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        markAllRead();
    });

    list.addEventListener('click', (event) => {
        const item = event.target.closest('.notif-item');
        if (!item) return;
        const notificationId = Number(item.dataset.id);
        if (!Number.isFinite(notificationId)) return;
        const clicked = notifications.find((n) => n.id === notificationId);
        if (!clicked) return;

        const targetHref = normalizeNotificationLink(clicked.enlace, clicked);
        if (targetHref && targetHref !== '#' && item.getAttribute('href') !== targetHref) {
            event.preventDefault();
            if (!clicked.leido) markNotificationRead(notificationId);
            close();
            window.location.assign(targetHref);
            return;
        }

        if (!clicked.leido) markNotificationRead(notificationId);
    });

    dropdown.addEventListener('click', (event) => event.stopPropagation());

    document.addEventListener('click', (event) => {
        if (!container.contains(event.target)) close();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') close();
    });

    window.addEventListener('beforeunload', stopSSE);

    startRealtime();
});
