(function () {
    'use strict';

    if (window.__adminSchoolSyncInit) return;
    window.__adminSchoolSyncInit = true;

    var API_URL = '/api/v1/admin/contexto-colegio/';
    var STORAGE_KEY = 'portal_admin_school_v1';
    var SYNC_INTERVAL_MS = 15000;
    var syncTimer = null;

    function clearStoredContext() {
        try {
            sessionStorage.removeItem(STORAGE_KEY);
            sessionStorage.removeItem('portal_admin_school_pending');
        } catch (e) { /* ignore */ }
    }

    function readBootstrap() {
        var node = document.getElementById('admin-school-bootstrap');
        if (!node) return null;
        try {
            return JSON.parse(node.textContent || '{}');
        } catch (e) {
            return null;
        }
    }

    function sameContext(a, b) {
        if (!a || !b) return false;
        return Boolean(a.activo) === Boolean(b.activo)
            && String(a.rbd || '') === String(b.rbd || '')
            && String(a.nombre || '') === String(b.nombre || '');
    }

    function storeContext(data) {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } catch (e) { /* ignore */ }
    }

    function getTargets() {
        return {
            sidebar: document.getElementById('admin-sidebar-school'),
            bar: document.getElementById('admin-school-context-bar'),
        };
    }

    function ensureSidebarShell() {
        var sidebar = document.getElementById('admin-sidebar-school');
        if (sidebar) return sidebar;

        var profile = document.querySelector('.adm-sidebar .pers-sidebar__profile');
        if (!profile) return null;

        sidebar = document.createElement('div');
        sidebar.id = 'admin-sidebar-school';
        sidebar.className = 'adm-sidebar-school';
        sidebar.setAttribute('data-admin-school-sync', 'sidebar');
        sidebar.hidden = true;
        sidebar.innerHTML = ''
            + '<p class="adm-sidebar-school__label">Colegio en gestión</p>'
            + '<p class="adm-sidebar-school__name" data-school-field="nombre"></p>'
            + '<span class="adm-badge adm-badge--mono adm-sidebar-school__rbd" data-school-field="rbd"></span>'
            + '<a href="/seleccionar-escuela/" class="adm-sidebar-school__link">Cambiar colegio</a>';
        profile.appendChild(sidebar);
        return sidebar;
    }

    function updateNode(root, data) {
        if (!root) return;

        var nameEl = root.querySelector('[data-school-field="nombre"]');
        var rbdEl = root.querySelector('[data-school-field="rbd"]');

        if (data.activo && data.rbd && data.nombre) {
            root.hidden = false;
            if (nameEl) nameEl.textContent = data.nombre;
            if (rbdEl) rbdEl.textContent = 'RBD ' + data.rbd;
            root.setAttribute('aria-label', 'Colegio en gestión: ' + data.nombre);
            return;
        }

        root.hidden = true;
    }

    function applyContext(data, options) {
        if (!data) return;

        var forceDom = options && options.forceDom;
        if (!forceDom) {
            var previous = null;
            try {
                previous = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
            } catch (e) { /* ignore */ }
            if (sameContext(previous, data)) return;
        }

        storeContext(data);
        ensureSidebarShell();

        var targets = getTargets();
        updateNode(targets.sidebar, data);
        updateNode(targets.bar, data);

        document.dispatchEvent(new CustomEvent('admin-school-context:updated', { detail: data }));
    }

    function fetchContext() {
        return fetch(API_URL, {
            method: 'GET',
            credentials: 'same-origin',
            headers: { Accept: 'application/json' },
            cache: 'no-store',
        }).then(function (response) {
            if (!response.ok) return null;
            return response.json();
        }).catch(function () {
            return null;
        });
    }

    function sync(options) {
        var opts = options || {};
        return fetchContext().then(function (data) {
            if (data) {
                applyContext(data, { forceDom: true });
                return data;
            }
            return null;
        });
    }

    function bootstrap() {
        clearStoredContext();

        var initial = readBootstrap();
        if (initial) {
            applyContext(initial, { forceDom: true });
        }

        var params = new URLSearchParams(window.location.search);
        if (params.get('school_ctx')) {
            sync({ forceDom: true });
            return;
        }

        sync({ forceDom: true });
    }

    function startPolling() {
        if (syncTimer) clearInterval(syncTimer);
        syncTimer = setInterval(function () {
            if (document.visibilityState !== 'visible') return;
            sync({ forceDom: false });
        }, SYNC_INTERVAL_MS);
    }

    document.addEventListener('click', function (event) {
        var link = event.target.closest('a[href*="/entrar-escuela/"]');
        if (link) {
            clearStoredContext();
            try {
                sessionStorage.setItem('portal_admin_school_pending', '1');
            } catch (e) { /* ignore */ }
            return;
        }

        var logoutBtn = event.target.closest('.pers-sidebar__logout-form button, form[action*="logout"] button');
        if (logoutBtn) {
            clearStoredContext();
        }
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootstrap);
    } else {
        bootstrap();
    }

    window.addEventListener('pageshow', function (event) {
        var pending = false;
        try {
            pending = sessionStorage.getItem('portal_admin_school_pending') === '1';
            if (pending) sessionStorage.removeItem('portal_admin_school_pending');
        } catch (e) { /* ignore */ }

        if (event.persisted || pending || window.location.search.indexOf('school_ctx=') !== -1) {
            clearStoredContext();
            sync({ forceDom: true });
        }
    });

    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible') {
            sync({ forceDom: false });
        }
    });

    startPolling();
})();
