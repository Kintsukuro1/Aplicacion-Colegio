/**
 * INICIO ADMIN - JAVASCRIPT
 * Scripts para el dashboard de administradores (admin general y admin_escolar)
 */

document.addEventListener('DOMContentLoaded', function() {
    initCardsAnimation();
    initRefreshStats();
});

/**
 * Inicializa la animación de las tarjetas
 */
function initCardsAnimation() {
    // Animar tarjetas de estadísticas
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
    // Animar tarjetas de escuelas
    const escuelaCards = document.querySelectorAll('.escuela-card');
    escuelaCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateX(0)';
        }, 400 + (index * 100));
    });
    
    // Animar tarjetas de acciones rápidas
    const actionCards = document.querySelectorAll('.quick-action-card');
    actionCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'scale(0.9)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'scale(1)';
        }, 600 + (index * 80));
    });
}

/**
 * Inicializa la actualización automática de estadísticas
 */
function initRefreshStats() {
    // Actualizar estadísticas cada 5 minutos
    setInterval(() => {
        actualizarEstadisticas();
    }, 5 * 60 * 1000);
}

/**
 * Actualiza las estadísticas del dashboard
 */
function actualizarEstadisticas() {
    const url = window.location.pathname;
    
    fetch(url + '?ajax=1', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Actualizar valores de las tarjetas de estadísticas
            actualizarValorStat('total_escuelas', data.total_escuelas);
            actualizarValorStat('total_usuarios', data.total_usuarios);
            actualizarValorStat('suscripciones_activas', data.suscripciones_activas);
            actualizarValorStat('suscripciones_vencidas', data.suscripciones_vencidas);
            actualizarValorStat('total_estudiantes', data.total_estudiantes);
            actualizarValorStat('total_profesores', data.total_profesores);
            actualizarValorStat('total_apoderados', data.total_apoderados);
            actualizarValorStat('total_cursos', data.total_cursos);
        }
    })
    .catch(error => {
        console.error('Error al actualizar estadísticas:', error);
    });
}

/**
 * Actualiza el valor de una tarjeta de estadística
 * @param {string} key - Clave de la estadística
 * @param {number} value - Nuevo valor
 */
function actualizarValorStat(key, value) {
    if (value === undefined) return;
    
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(card => {
        const valueElement = card.querySelector('.stat-value');
        if (valueElement && valueElement.dataset.key === key) {
            const currentValue = parseInt(valueElement.textContent);
            if (currentValue !== value) {
                animarCambioValor(valueElement, currentValue, value);
            }
        }
    });
}

/**
 * Anima el cambio de valor en una tarjeta
 * @param {HTMLElement} element - Elemento que contiene el valor
 * @param {number} from - Valor inicial
 * @param {number} to - Valor final
 */
function animarCambioValor(element, from, to) {
    const duration = 500;
    const steps = 20;
    const stepDuration = duration / steps;
    const increment = (to - from) / steps;
    let current = from;
    let step = 0;
    
    const interval = setInterval(() => {
        step++;
        current += increment;
        element.textContent = Math.round(current);
        
        if (step >= steps) {
            clearInterval(interval);
            element.textContent = to;
        }
    }, stepDuration);
    
    // Efecto visual de actualización
    element.style.transition = 'transform 0.3s ease';
    element.style.transform = 'scale(1.1)';
    setTimeout(() => {
        element.style.transform = 'scale(1)';
    }, 300);
}

/**
 * Muestra un toast de notificación
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de toast ('success', 'error', 'warning', 'info')
 */
function showToast(message, type = 'info') {
    // Eliminar toasts existentes
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Crear nuevo toast
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };
    
    toast.style.cssText = `
        position: fixed;
        top: 2rem;
        right: 2rem;
        background: white;
        color: #1f2937;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border-left: 4px solid ${colors[type]};
        z-index: 10000;
        animation: slideInRight 0.3s ease;
        max-width: 400px;
    `;
    
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}" 
               style="color: ${colors[type]}; font-size: 1.25rem;"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-cerrar después de 5 segundos
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Estilos CSS para animaciones de toast
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
