/**
 * INICIO - APODERADO
 * Dashboard principal para apoderados
 */

document.addEventListener('DOMContentLoaded', function() {
    initDashboardApoderado();
});

/**
 * Inicializa el dashboard
 */
function initDashboardApoderado() {
    initCardsAnimation();
    showWelcomeMessage();
    checkPendingNotifications();
    
    console.log('Dashboard de apoderado inicializado');
}

/**
 * Anima la aparición de las tarjetas
 */
function initCardsAnimation() {
    // Animar stat cards
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
    
    // Animar hijo cards
    const hijoCards = document.querySelectorAll('.hijo-card');
    hijoCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateX(0)';
        }, 200 + (index * 100));
    });
    
    // Animar quick action cards
    const actionCards = document.querySelectorAll('.quick-action-card');
    actionCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'scale(0.95)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'scale(1)';
        }, 400 + (index * 75));
    });
    
    // Animar comunicados
    const comunicados = document.querySelectorAll('.comunicado-item');
    comunicados.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            item.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, 600 + (index * 100));
    });
}

/**
 * Muestra mensaje de bienvenida
 */
function showWelcomeMessage() {
    setTimeout(() => {
        showToast('¡Bienvenido/a al portal de apoderados! 👨‍👩‍👧‍👦', 'success');
    }, 500);
}

/**
 * Verifica notificaciones pendientes
 */
function checkPendingNotifications() {
    // Verificar comunicados nuevos
    const comunicadosNuevos = document.querySelectorAll('.comunicado-icon.nuevo').length;
    if (comunicadosNuevos > 0) {
        setTimeout(() => {
            showToast(`Tienes ${comunicadosNuevos} comunicado${comunicadosNuevos > 1 ? 's' : ''} nuevo${comunicadosNuevos > 1 ? 's' : ''}`, 'info');
        }, 2000);
    }
    
    // Verificar pendientes de firma
    const pendientesFirma = document.querySelector('.stat-card:nth-child(3) .stat-value')?.textContent.trim();
    if (pendientesFirma && parseInt(pendientesFirma) > 0) {
        setTimeout(() => {
            showToast(`Tienes ${pendientesFirma} autorización${parseInt(pendientesFirma) > 1 ? 'es' : ''} pendiente${parseInt(pendientesFirma) > 1 ? 's' : ''} de firma`, 'warning');
        }, 3000);
    }
}

/**
 * Redirige a notas del hijo
 * @param {number} estudianteId - ID del estudiante
 */
function verNotasHijo(estudianteId) {
    if (!estudianteId) return;
    window.location.href = `/academico/notas/hijo/?estudiante_id=${estudianteId}`;
}

/**
 * Redirige a asistencia del hijo
 * @param {number} estudianteId - ID del estudiante
 */
function verAsistenciaHijo(estudianteId) {
    if (!estudianteId) return;
    window.location.href = `/academico/asistencia/hijo/?estudiante_id=${estudianteId}`;
}

/**
 * Redirige a tareas del hijo
 * @param {number} estudianteId - ID del estudiante
 */
function verTareasHijo(estudianteId) {
    if (!estudianteId) return;
    window.location.href = `/academico/tareas/hijo/?estudiante_id=${estudianteId}`;
}

/**
 * Marca comunicado como leído
 * @param {number} comunicadoId - ID del comunicado
 */
function marcarComunicadoLeido(comunicadoId) {
    if (!comunicadoId) return;
    
    fetch(`/api/comunicados/${comunicadoId}/marcar-leido/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Actualizar UI
            const iconoElement = document.querySelector(`[data-comunicado-id="${comunicadoId}"] .comunicado-icon`);
            if (iconoElement) {
                iconoElement.classList.remove('nuevo');
            }
        }
    })
    .catch(error => {
        console.error('Error al marcar comunicado como leído:', error);
    });
}

/**
 * Obtiene el token CSRF
 * @returns {string} Token CSRF
 */
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

/**
 * Actualiza estadísticas en tiempo real
 */
function actualizarEstadisticas() {
    fetch('/api/apoderado/estadisticas/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        // Actualizar valores en los stat cards
        if (data.comunicados_nuevos !== undefined) {
            const comunicadosCard = document.querySelector('.stat-card:nth-child(2) .stat-value');
            if (comunicadosCard) {
                comunicadosCard.textContent = data.comunicados_nuevos;
            }
        }
        
        if (data.pendientes_firma !== undefined) {
            const firmaCard = document.querySelector('.stat-card:nth-child(3) .stat-value');
            if (firmaCard) {
                firmaCard.textContent = data.pendientes_firma;
            }
        }
        
        if (data.cuotas_pendientes !== undefined) {
            const cuotasCard = document.querySelector('.stat-card:nth-child(4) .stat-value');
            if (cuotasCard) {
                cuotasCard.textContent = data.cuotas_pendientes;
            }
        }
    })
    .catch(error => {
        console.error('Error al actualizar estadísticas:', error);
    });
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

// Actualizar estadísticas cada 5 minutos
setInterval(actualizarEstadisticas, 5 * 60 * 1000);
