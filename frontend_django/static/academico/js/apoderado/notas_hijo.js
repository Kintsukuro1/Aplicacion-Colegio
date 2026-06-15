/**
 * NOTAS HIJO - APODERADO
 * Gestión de la vista de calificaciones del hijo
 */

document.addEventListener('DOMContentLoaded', function() {
    initNotasHijo();
});

/**
 * Inicializa la funcionalidad de la página
 */
function initNotasHijo() {
    initSelectorHijo();
    initCardsAnimation();
    initTooltips();
    
    console.log('Vista de notas del hijo inicializada');
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
        
        // Highlight del hijo seleccionado
        selector.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        selector.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
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
    const container = document.querySelector('.notas-container');
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
 * Anima la aparición de las tarjetas
 */
function initCardsAnimation() {
    const cards = document.querySelectorAll('.asignatura-card');
    
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 50);
    });
}

/**
 * Inicializa tooltips para información adicional
 */
function initTooltips() {
    const promedioValor = document.querySelector('.promedio-valor');
    
    if (promedioValor) {
        const valor = parseFloat(promedioValor.textContent);
        
        if (!isNaN(valor)) {
            let mensaje = '';
            
            if (valor >= 5.5) {
                mensaje = 'Excelente rendimiento académico';
            } else if (valor >= 5.0) {
                mensaje = 'Buen rendimiento académico';
            } else if (valor >= 4.0) {
                mensaje = 'Rendimiento suficiente';
            } else {
                mensaje = 'Necesita mejorar - Considere apoyo adicional';
            }
            
            promedioValor.setAttribute('title', mensaje);
        }
    }
}

/**
 * Filtra asignaturas por término de búsqueda
 * @param {string} searchTerm - Término de búsqueda
 */
function filtrarAsignaturas(searchTerm) {
    const cards = document.querySelectorAll('.asignatura-card');
    const term = searchTerm.toLowerCase().trim();
    
    cards.forEach(card => {
        const nombre = card.querySelector('.asignatura-nombre')?.textContent.toLowerCase() || '';
        const codigo = card.querySelector('.asignatura-codigo')?.textContent.toLowerCase() || '';
        
        if (nombre.includes(term) || codigo.includes(term) || term === '') {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

/**
 * Exporta notas a PDF (función placeholder)
 */
function exportarNotasPDF() {
    const estudianteId = document.getElementById('hijoSelect')?.value;
    
    if (!estudianteId) {
        alert('Por favor seleccione un estudiante');
        return;
    }
    
    // Abrir descarga real del certificado de notas en PDF (ReportLab)
    window.open('/pdf/certificado-notas/' + estudianteId + '/', '_blank');
}

/**
 * Muestra notificación toast
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de notificación (success, error, info)
 */
function showToast(message, type = 'info') {
    // Implementación simple de toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
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
