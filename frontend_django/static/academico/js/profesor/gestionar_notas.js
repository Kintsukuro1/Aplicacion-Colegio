/** GESTIONAR NOTAS - PROFESOR */

document.addEventListener('DOMContentLoaded', function() {
    initTableAnimations();
});

// Abrir modal crear evaluación
function abrirModalCrearEvaluacion() {
    document.getElementById('modal-crear-evaluacion').style.display = 'flex';
}

// Cerrar modal crear evaluación
function cerrarModalCrearEvaluacion() {
    document.getElementById('modal-crear-evaluacion').style.display = 'none';
    document.getElementById('form-crear-evaluacion').reset();
}

// Submit crear evaluación
function submitCrearEvaluacion() {
    const form = document.getElementById('form-crear-evaluacion');
    
    if (form.checkValidity()) {
        form.submit();
    } else {
        form.reportValidity();
    }
}

// Calificar evaluación
function calificarEvaluacion(evaluacionId) {
    const urlParams = new URLSearchParams(window.location.search);
    const claseId = urlParams.get('clase_id');
    let url = `?pagina=notas&modo=calificar&evaluacion_id=${evaluacionId}`;
    if (claseId) {
        url += `&clase_id=${claseId}`;
    }
    window.location.href = url;
}

// Editar evaluación
function editarEvaluacion(evaluacionId, nombre, fecha, ponderacion) {
    document.getElementById('editar_evaluacion_id').value = evaluacionId;
    document.getElementById('editar_nombre_evaluacion').value = nombre;
    document.getElementById('editar_fecha_evaluacion').value = fecha;
    document.getElementById('editar_ponderacion').value = ponderacion;
    document.getElementById('modal-editar-evaluacion').style.display = 'flex';
}

// Cerrar modal editar evaluación
function cerrarModalEditarEvaluacion() {
    document.getElementById('modal-editar-evaluacion').style.display = 'none';
    document.getElementById('form-editar-evaluacion').reset();
}

// Submit editar evaluación
function submitEditarEvaluacion() {
    const form = document.getElementById('form-editar-evaluacion');
    if (form.checkValidity()) {
        form.submit();
    } else {
        form.reportValidity();
    }
}

// Eliminar evaluación
function eliminarEvaluacion(evaluacionId) {
    if (confirm('¿Estás seguro de eliminar esta evaluación? Se eliminarán todas las calificaciones asociadas.')) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.innerHTML = `
            <input type="hidden" name="csrfmiddlewaretoken" value="${getCsrfToken()}">
            <input type="hidden" name="accion" value="eliminar_evaluacion">
            <input type="hidden" name="id" value="${evaluacionId}">
        `;
        document.body.appendChild(form);
        form.submit();
    }
}

// Obtener CSRF token
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

// Animaciones de tabla
function initTableAnimations() {
    const rows = document.querySelectorAll('.table tbody tr');
    rows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateY(10px)';
        
        setTimeout(() => {
            row.style.transition = 'all 0.3s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, index * 50);
    });
}

// Cerrar modal con ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal-backdrop');
        modals.forEach(modal => {
            if (modal.style.display === 'flex') {
                modal.style.display = 'none';
            }
        });
    }
});
