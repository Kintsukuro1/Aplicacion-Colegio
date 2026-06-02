/** GESTIONAR TAREAS - PROFESOR */

function mostrarModalCrear() {
    const modal = document.getElementById('modalCrearTarea');
    modal.style.display = 'flex';
    actualizarSeccionOnline();

    // Establecer fecha mínima como ahora
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    const campoFecha = document.getElementById('fecha_entrega');
    if (campoFecha) {
        campoFecha.min = now.toISOString().slice(0, 16);
    }
}

function cerrarModalCrear() {
    const modal = document.getElementById('modalCrearTarea');
    const form = document.getElementById('formCrearTarea');
    if (modal) {
        modal.style.display = 'none';
    }
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
    seccionOnline.classList.toggle('hidden', !mostrar);
}

document.addEventListener('change', function (event) {
    if (event.target && event.target.matches('[data-modalidad-select]')) {
        actualizarSeccionOnline();
    }
});

document.addEventListener('DOMContentLoaded', function () {
    actualizarSeccionOnline();

    // Auto-abrir modal si la URL contiene ?crear=1 (Reducir clics)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('crear') === '1') {
        mostrarModalCrear();
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
