/**
 * TAREAS HIJO - APODERADO
 * Gestión de la vista de tareas del hijo
 */

document.addEventListener('DOMContentLoaded', function() {
    initTareasHijo();
});

/**
 * Inicializa la funcionalidad de la página
 */
function initTareasHijo() {
    initSelectorHijo();
    initAnimaciones();
    initFiltros();
    
    console.log('Vista de tareas del hijo inicializada');
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
    const container = document.querySelector('.tareas-container');
    if (container) {
        container.style.opacity = '0.6';
        container.style.pointerEvents = 'none';
    }
    
    // Construir URL con parámetro
    const url = new URL(window.location.href);
    url.searchParams.set('estudiante_id', estudianteId);
    
    // Redirigir
    window.location.href = url.toString();
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
    
    // Animar tarjetas de tareas
    const tareaCards = document.querySelectorAll('.tarea-card');
    tareaCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 75);
    });
}

/**
 * Inicializa los filtros
 */
function initFiltros() {
    // Los filtros ya tienen onchange="this.form.submit()"
    // Aquí podemos agregar funcionalidad adicional si es necesaria
}

/**
 * Muestra el detalle de una tarea
 * @param {number} tareaId - ID de la tarea
 */
function verDetalleTarea(tareaId) {
    if (!tareaId) return;
    
    // Redirigir a página de detalle
    window.location.href = `/academico/tareas/${tareaId}/detalle/`;
}

/**
 * Filtra tareas por búsqueda de texto
 * @param {string} searchTerm - Término de búsqueda
 */
function filtrarTareasPorTexto(searchTerm) {
    const cards = document.querySelectorAll('.tarea-card');
    const term = searchTerm.toLowerCase().trim();
    
    cards.forEach(card => {
        const titulo = card.querySelector('.tarea-titulo')?.textContent.toLowerCase() || '';
        const descripcion = card.querySelector('.tarea-descripcion')?.textContent.toLowerCase() || '';
        const asignatura = card.querySelector('.meta-item i.fa-book')?.parentElement.textContent.toLowerCase() || '';
        
        if (titulo.includes(term) || descripcion.includes(term) || asignatura.includes(term) || term === '') {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
    
    // Mostrar mensaje si no hay resultados
    const visibleCards = Array.from(cards).filter(card => card.style.display !== 'none');
    
    if (visibleCards.length === 0 && term !== '') {
        showToast(`No se encontraron tareas que coincidan con "${searchTerm}"`, 'info');
    }
}

/**
 * Ordena tareas por diferentes criterios
 * @param {string} criterio - Criterio de ordenamiento (fecha, estado, asignatura)
 */
function ordenarTareas(criterio) {
    const container = document.querySelector('.tareas-grid');
    if (!container) return;
    
    const cards = Array.from(container.querySelectorAll('.tarea-card'));
    
    cards.sort((a, b) => {
        switch (criterio) {
            case 'fecha':
                // Ordenar por fecha de entrega
                const fechaA = a.querySelector('.meta-item i.fa-calendar')?.parentElement.textContent || '';
                const fechaB = b.querySelector('.meta-item i.fa-calendar')?.parentElement.textContent || '';
                return fechaA.localeCompare(fechaB);
                
            case 'estado':
                // Ordenar por estado (pendiente, entregada, calificada, atrasada)
                const estadoOrder = { 'pendiente': 1, 'atrasada': 2, 'entregada': 3, 'calificada': 4 };
                const estadoA = a.querySelector('.badge')?.classList[1]?.replace('badge-', '') || '';
                const estadoB = b.querySelector('.badge')?.classList[1]?.replace('badge-', '') || '';
                return (estadoOrder[estadoA] || 0) - (estadoOrder[estadoB] || 0);
                
            case 'asignatura':
                // Ordenar por asignatura
                const asigA = a.querySelector('.meta-item i.fa-book')?.parentElement.textContent || '';
                const asigB = b.querySelector('.meta-item i.fa-book')?.parentElement.textContent || '';
                return asigA.localeCompare(asigB);
                
            default:
                return 0;
        }
    });
    
    // Limpiar y volver a agregar en orden
    cards.forEach(card => container.appendChild(card));
    
    showToast(`Tareas ordenadas por ${criterio}`, 'success');
}

/**
 * Exporta tareas a PDF
 */
function exportarTareasPDF() {
    const estudianteId = document.getElementById('hijoSelect')?.value;
    
    if (!estudianteId) {
        showToast('Por favor seleccione un estudiante', 'error');
        return;
    }
    
    // Construir URL de exportación
    let url = `/api/academico/tareas/pdf/?estudiante_id=${estudianteId}`;
    
    // Agregar filtros si existen
    const urlParams = new URLSearchParams(window.location.search);
    const estado = urlParams.get('estado');
    const asignatura = urlParams.get('asignatura');
    
    if (estado) url += `&estado=${estado}`;
    if (asignatura) url += `&asignatura=${asignatura}`;
    
    window.open(url, '_blank');
}

/**
 * Calcula estadísticas de tareas
 */
function calcularEstadisticasTareas() {
    const cards = document.querySelectorAll('.tarea-card');
    
    let stats = {
        total: cards.length,
        pendientes: 0,
        entregadas: 0,
        calificadas: 0,
        atrasadas: 0,
        urgentes: 0,
        vencidas: 0
    };
    
    cards.forEach(card => {
        if (card.classList.contains('urgente')) stats.urgentes++;
        if (card.classList.contains('vencida')) stats.vencidas++;
        
        const badge = card.querySelector('.badge');
        if (badge) {
            if (badge.classList.contains('badge-pendiente')) stats.pendientes++;
            if (badge.classList.contains('badge-entregada')) stats.entregadas++;
            if (badge.classList.contains('badge-calificada')) stats.calificadas++;
            if (badge.classList.contains('badge-atrasada')) stats.atrasadas++;
        }
    });
    
    return stats;
}

/**
 * Muestra notificación toast
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de notificación (success, error, info, warning)
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
