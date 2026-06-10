/** GESTIONAR TAREAS - PROFESOR */

function _getModalCrear() {
    const modal = document.getElementById('modalCrearTarea');
    if (!modal) {
        return null;
    }
    if (modal.parentElement !== document.body) {
        document.body.appendChild(modal);
    }
    return modal;
}

function _abrirModalCrear() {
    const modal = _getModalCrear();
    if (!modal) {
        return;
    }
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('gt-modal-open');
    actualizarSeccionOnline();

    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    const campoFecha = document.getElementById('fecha_entrega');
    if (campoFecha) {
        campoFecha.min = now.toISOString().slice(0, 16);
    }
}

function mostrarModalCrear() {
    _abrirModalCrear();
}

function cerrarModalCrear() {
    const modal = document.getElementById('modalCrearTarea');
    const form = document.getElementById('formCrearTarea');
    if (modal) {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
    }
    document.body.classList.remove('gt-modal-open');
    if (form) {
        form.reset();
    }
}

function submitCrearTarea() {
    const form = document.getElementById('formCrearTarea');
    if (form.checkValidity()) {
        form.submit();
    } else {
        form.reportValidity();
    }
}

function actualizarSeccionOnline() {
    const selectorModalidad = document.querySelector('[data-modalidad-select]');
    const seccionOnline = document.querySelector('[data-online-section]');

    if (!selectorModalidad || !seccionOnline) {
        return;
    }

    const modalidad = selectorModalidad.value;
    const mostrar = modalidad === 'ONLINE' || modalidad === 'MIXTA';
    seccionOnline.classList.toggle('gt-hidden', !mostrar);
}

document.addEventListener('change', function (event) {
    if (event.target && event.target.matches('[data-modalidad-select]')) {
        actualizarSeccionOnline();
    }
});

document.addEventListener('DOMContentLoaded', function () {
    const modal = _getModalCrear();
    actualizarSeccionOnline();

    if (modal) {
        const scrim = modal.querySelector('.gt-modal-root__scrim');
        if (scrim) {
            scrim.addEventListener('click', cerrarModalCrear);
        }
    }

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('crear') === '1') {
        _abrirModalCrear();
    }
});

document.addEventListener('keydown', function (event) {
    const modal = document.getElementById('modalCrearTarea');
    if (event.key === 'Escape' && modal && modal.classList.contains('is-open')) {
        cerrarModalCrear();
    }
});

function eliminarTarea(tareaId) {
    if (confirm('¿Eliminar esta tarea? Se eliminarán todas las entregas asociadas.')) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.innerHTML = `
            <input type="hidden" name="csrfmiddlewaretoken" value="${getCsrfToken()}">
            <input type="hidden" name="accion" value="eliminar_tarea">
            <input type="hidden" name="tarea_id" value="${tareaId}">
        `;
        document.body.appendChild(form);
        form.submit();
    }
}

function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
