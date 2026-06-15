/**
 * ASISTENCIA HIJO - APODERADO
 * Gestión de la vista de asistencia del hijo
 */

document.addEventListener('DOMContentLoaded', function() {
    initAsistenciaHijo();
});

/**
 * Inicializa la funcionalidad de la página
 */
function initAsistenciaHijo() {
    initSelectorHijo();
    initFiltros();
    initAnimaciones();
    
    console.log('Vista de asistencia del hijo inicializada');
}

/**
 * Inicializa el selector de hijo
 */
function initSelectorHijo() {
    const selector = document.getElementById('hijoSelect');
    
    if (selector) {
        selector.addEventListener('change', function() {
            const selectedValue = this.value;
            cambiarHijo(selectedValue);
        });
    }
}

/**
 * Cambia el hijo seleccionado y recarga la página
 * @param {string} estudianteId - ID del estudiante seleccionado
 */
function cambiarHijo(estudianteId) {
    if (!estudianteId) return;
    
    // Mostrar indicador de carga
    const container = document.querySelector('.asistencia-container');
    if (container) {
        container.style.opacity = '0.6';
        container.style.pointerEvents = 'none';
    }
    
    // Construir URL con parámetro
    const url = new URL(window.location.href);
    url.searchParams.set('estudiante_id', estudianteId);
    
    // Mantener otros filtros si existen
    const periodoFilter = document.getElementById('periodoFilter');
    const asignaturaFilter = document.getElementById('asignaturaFilter');
    
    if (periodoFilter && periodoFilter.value) {
        url.searchParams.set('periodo', periodoFilter.value);
    }
    
    if (asignaturaFilter && asignaturaFilter.value) {
        url.searchParams.set('asignatura', asignaturaFilter.value);
    }
    
    // Redirigir
    window.location.href = url.toString();
}

/**
 * Inicializa los filtros
 */
function initFiltros() {
    const form = document.getElementById('filtrosForm');
    
    if (form) {
        // Cambio automático en período
        const periodoSelect = document.getElementById('periodoFilter');
        if (periodoSelect) {
            periodoSelect.addEventListener('change', function() {
                form.submit();
            });
        }
        
        // Cambio automático en asignatura
        const asignaturaSelect = document.getElementById('asignaturaFilter');
        if (asignaturaSelect) {
            asignaturaSelect.addEventListener('change', function() {
                form.submit();
            });
        }
    }
}

/**
 * Limpia los filtros y recarga la página
 */
function limpiarFiltros() {
    const url = new URL(window.location.href);
    const estudianteId = document.getElementById('hijoSelect')?.value;
    
    // Limpiar todos los parámetros excepto estudiante_id
    const newUrl = new URL(url.origin + url.pathname);
    if (estudianteId) {
        newUrl.searchParams.set('estudiante_id', estudianteId);
    }
    
    window.location.href = newUrl.toString();
}

/**
 * Inicializa animaciones de entrada
 */
function initAnimaciones() {
    // Animar tarjetas de estadísticas
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 50);
    });
    
    // Animar grupos de fecha
    const fechaGrupos = document.querySelectorAll('.fecha-grupo');
    fechaGrupos.forEach((grupo, index) => {
        grupo.style.opacity = '0';
        grupo.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            grupo.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            grupo.style.opacity = '1';
            grupo.style.transform = 'translateX(0)';
        }, index * 100);
    });
}

/**
 * Exporta asistencia a PDF
 */
function exportarAsistenciaPDF() {
    const estudianteId = document.getElementById('hijoSelect')?.value;
    
    if (!estudianteId) {
        showToast('Por favor seleccione un estudiante', 'error');
        return;
    }
    
    const periodoFilter = document.getElementById('periodoFilter')?.value;
    const asignaturaFilter = document.getElementById('asignaturaFilter')?.value;
    
    // Construir URL de exportación
    let url = `/api/academico/asistencia/pdf/?estudiante_id=${estudianteId}`;
    
    if (periodoFilter) {
        url += `&periodo=${periodoFilter}`;
    }
    
    if (asignaturaFilter) {
        url += `&asignatura=${asignaturaFilter}`;
    }
    
    window.open(url, '_blank');
}

/**
 * Filtra registros por fecha
 * @param {string} fechaInicio - Fecha de inicio (YYYY-MM-DD)
 * @param {string} fechaFin - Fecha de fin (YYYY-MM-DD)
 */
function filtrarPorRangoFecha(fechaInicio, fechaFin) {
    const url = new URL(window.location.href);
    const estudianteId = document.getElementById('hijoSelect')?.value;
    
    if (estudianteId) {
        url.searchParams.set('estudiante_id', estudianteId);
    }
    
    if (fechaInicio) {
        url.searchParams.set('fecha_inicio', fechaInicio);
    }
    
    if (fechaFin) {
        url.searchParams.set('fecha_fin', fechaFin);
    }
    
    window.location.href = url.toString();
}

/**
 * Muestra detalles de un registro de asistencia en un modal premium
 * @param {string} id - ID del registro
 * @param {string} asignatura - Nombre de la asignatura
 * @param {string} fecha - Fecha del registro
 * @param {string} estado - Estado en texto (Presente, Ausente, etc.)
 * @param {string} observacion - Comentarios u observaciones del docente
 */
function verDetalleRegistro(id, asignatura, fecha, estado, observacion) {
    document.getElementById('detalle-asignatura').textContent = asignatura;
    document.getElementById('detalle-fecha').textContent = fecha;
    
    const badge = document.getElementById('detalle-estado-badge');
    badge.textContent = estado;
    
    // Limpiar y aplicar clases correctas de color al badge
    badge.className = 'badge';
    const estLower = estado.toLowerCase();
    if (estLower.includes('pres')) {
        badge.classList.add('badge-success');
    } else if (estLower.includes('aus')) {
        badge.classList.add('badge-danger');
    } else if (estLower.includes('atr') || estLower.includes('tard')) {
        badge.classList.add('badge-warning');
    } else if (estLower.includes('jus')) {
        badge.classList.add('badge-info');
    }
    
    const obsElement = document.getElementById('detalle-observacion');
    if (observacion && observacion.trim() !== '') {
        obsElement.textContent = observacion;
    } else {
        obsElement.textContent = 'Sin observaciones o comentarios registrados para este bloque.';
    }
    
    const modal = document.getElementById('modal-detalle-asistencia');
    const dialog = modal.querySelector('.modal-dialog');
    
    modal.style.display = 'flex';
    // Forzar reflow para la animación
    modal.offsetHeight;
    
    modal.style.opacity = '1';
    modal.style.pointerEvents = 'auto';
    if (dialog) {
        dialog.style.transform = 'scale(1)';
    }
}

/**
 * Cierra el modal de detalle de asistencia con transiciones suaves
 */
function cerrarModalDetalle() {
    const modal = document.getElementById('modal-detalle-asistencia');
    const dialog = modal.querySelector('.modal-dialog');
    
    modal.style.opacity = '0';
    modal.style.pointerEvents = 'none';
    if (dialog) {
        dialog.style.transform = 'scale(0.9)';
    }
    
    setTimeout(() => {
        modal.style.display = 'none';
    }, 300);
}

// Escuchar tecla escape para cerrar el modal
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('modal-detalle-asistencia');
        if (modal && modal.style.display === 'flex') {
            cerrarModalDetalle();
        }
    }
});

/**
 * Calcula y muestra estadísticas personalizadas
 */
function calcularEstadisticas() {
    const registros = document.querySelectorAll('.registro-item');
    
    let stats = {
        total: registros.length,
        presentes: 0,
        ausentes: 0,
        atrasos: 0,
        justificadas: 0
    };
    
    registros.forEach(registro => {
        const badge = registro.querySelector('.badge');
        if (badge) {
            if (badge.classList.contains('badge-success')) stats.presentes++;
            if (badge.classList.contains('badge-danger')) stats.ausentes++;
            if (badge.classList.contains('badge-warning')) stats.atrasos++;
            if (badge.classList.contains('badge-info')) stats.justificadas++;
        }
    });
    
    return stats;
}

/**
 * Muestra notificación toast
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de notificación (success, error, info)
 */
function showToast(message, type = 'info') {
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        info: '#3b82f6',
        warning: '#f59e0b'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        padding: 1rem 1.5rem;
        background: ${colors[type] || colors.info};
        color: white;
        border-radius: 0.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
