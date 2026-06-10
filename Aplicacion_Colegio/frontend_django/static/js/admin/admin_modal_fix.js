/**
 * Bootstrap y modales custom dentro del portal admin: mover al body y limpiar backdrops.
 */
(function () {
    function relocateOverlays() {
        document.querySelectorAll('.modal, .modal-overlay').forEach(function (el) {
            if (el.parentElement !== document.body) {
                document.body.appendChild(el);
            }
        });
    }

    function cleanupBackdrops() {
        var backdrops = document.querySelectorAll('.modal-backdrop');
        if (backdrops.length > 1) {
            backdrops.forEach(function (backdrop, index) {
                if (index < backdrops.length - 1) {
                    backdrop.remove();
                }
            });
        }
        if (!document.querySelector('.modal.show') && !document.querySelector('.modal-overlay.active')) {
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');
            document.querySelectorAll('.modal-backdrop').forEach(function (b) { b.remove(); });
        }
    }

    function resetModalForm(modalEl) {
        if (!modalEl || !modalEl.id) return;
        modalEl.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(function (field) {
            if (field.type === 'checkbox' || field.type === 'radio') {
                field.checked = field.defaultChecked;
            } else {
                field.value = field.defaultValue || '';
            }
        });
    }

    function bindModal(el) {
        if (el.dataset.admModalBound === '1') return;
        el.dataset.admModalBound = '1';
        el.addEventListener('hidden.bs.modal', function () {
            cleanupBackdrops();
            resetModalForm(el);
        });
        el.addEventListener('shown.bs.modal', cleanupBackdrops);
    }

    function init() {
        relocateOverlays();
        cleanupBackdrops();
        document.querySelectorAll('.modal').forEach(bindModal);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.AdminModal = {
        getInstance: function (id) {
            var el = document.getElementById(id);
            if (!el || typeof bootstrap === 'undefined') return null;
            relocateOverlays();
            return bootstrap.Modal.getOrCreateInstance(el);
        },
        hide: function (id) {
            var instance = window.AdminModal.getInstance(id);
            if (instance) instance.hide();
            cleanupBackdrops();
        },
        show: function (id) {
            var instance = window.AdminModal.getInstance(id);
            if (instance) instance.show();
        },
        resetForm: resetModalForm,
        cleanup: cleanupBackdrops,
    };
})();
