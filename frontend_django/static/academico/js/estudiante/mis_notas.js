/**
 * MIS NOTAS - ESTUDIANTE
 * JavaScript para funcionalidad interactiva de la vista de notas
 */

document.addEventListener('DOMContentLoaded', function() {
    initGradeAnimations();
    initTableFilters();
    initPrintPreview();
});

/**
 * Anima las barras de progreso y círculos de promedio
 */
function initGradeAnimations() {
    // Animar progress bars
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const targetWidth = bar.style.width;
        bar.style.width = '0%';
        
        // Trigger animation after a small delay
        setTimeout(() => {
            bar.style.width = targetWidth;
        }, 100);
    });
    
    // Animar círculos de promedio
    const gradeCircles = document.querySelectorAll('.grade-circle');
    gradeCircles.forEach((circle, index) => {
        circle.style.opacity = '0';
        circle.style.transform = 'scale(0.5)';
        
        setTimeout(() => {
            circle.style.transition = 'all 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)';
            circle.style.opacity = '1';
            circle.style.transform = 'scale(1)';
        }, 100 * index);
    });
}

/**
 * Inicializa filtros de búsqueda en las tablas
 */
function initTableFilters() {
    // Agregar búsqueda rápida por asignatura
    const searchInput = createSearchInput();
    if (searchInput) {
        const container = document.querySelector('.mb-xl h2');
        if (container && container.parentElement) {
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.justifyContent = 'space-between';
            wrapper.style.alignItems = 'center';
            wrapper.style.marginBottom = 'var(--spacing-lg)';
            wrapper.style.flexWrap = 'wrap';
            wrapper.style.gap = 'var(--spacing-md)';
            
            container.parentElement.insertBefore(wrapper, container);
            wrapper.appendChild(container);
            wrapper.appendChild(searchInput);
        }
    }
}

/**
 * Crea input de búsqueda
 */
function createSearchInput() {
    const subjects = document.querySelectorAll('.subject-card');
    if (subjects.length === 0) return null;
    
    const wrapper = document.createElement('div');
    wrapper.style.position = 'relative';
    wrapper.style.maxWidth = '300px';
    
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Buscar asignatura...';
    input.className = 'form-input';
    input.style.paddingLeft = 'calc(var(--spacing-md) + 24px)';
    
    const icon = document.createElement('i');
    icon.className = 'fas fa-search';
    icon.style.position = 'absolute';
    icon.style.left = 'var(--spacing-md)';
    icon.style.top = '50%';
    icon.style.transform = 'translateY(-50%)';
    icon.style.color = 'var(--color-text-tertiary)';
    icon.style.pointerEvents = 'none';
    
    wrapper.appendChild(icon);
    wrapper.appendChild(input);
    
    // Lógica de filtrado
    input.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        
        subjects.forEach(subject => {
            const subjectName = subject.querySelector('.subject-header h3').textContent.toLowerCase();
            const professorName = subject.querySelector('.subject-header p').textContent.toLowerCase();
            
            if (subjectName.includes(searchTerm) || professorName.includes(searchTerm)) {
                subject.style.display = '';
                // Animate in
                subject.style.animation = 'fadeIn 0.3s ease';
            } else {
                subject.style.display = 'none';
            }
        });
        
        // Mostrar mensaje si no hay resultados
        checkEmptyResults(subjects);
    });
    
    return wrapper;
}

/**
 * Verifica si hay resultados de búsqueda
 */
function checkEmptyResults(subjects) {
    const visibleSubjects = Array.from(subjects).filter(s => s.style.display !== 'none');
    
    let emptyMessage = document.getElementById('empty-search-result');
    
    if (visibleSubjects.length === 0) {
        if (!emptyMessage) {
            emptyMessage = document.createElement('div');
            emptyMessage.id = 'empty-search-result';
            emptyMessage.className = 'text-center text-secondary';
            emptyMessage.style.padding = 'var(--spacing-3xl)';
            emptyMessage.innerHTML = `
                <i class="fas fa-search" style="font-size: 3rem; opacity: 0.3; margin-bottom: var(--spacing-md);"></i>
                <p class="text-lg">No se encontraron asignaturas que coincidan con tu búsqueda</p>
            `;
            
            const container = subjects[0].parentElement;
            container.appendChild(emptyMessage);
        }
    } else {
        if (emptyMessage) {
            emptyMessage.remove();
        }
    }
}

/**
 * Optimiza la impresión
 */
function initPrintPreview() {
    // Expandir todas las tablas antes de imprimir
    window.addEventListener('beforeprint', function() {
        // Guardar estados colapsados si los hay
        console.log('Preparando para imprimir...');
    });
    
    window.addEventListener('afterprint', function() {
        // Restaurar estados
        console.log('Impresión finalizada');
    });
}

/**
 * Calcula estadísticas adicionales (para uso futuro)
 */
function calculateStatistics() {
    const gradeElements = document.querySelectorAll('.subject-card');
    let totalGrades = 0;
    let sumGrades = 0;
    let approved = 0;
    let failed = 0;
    
    gradeElements.forEach(card => {
        const gradeText = card.querySelector('.grade-circle .text-2xl');
        if (gradeText) {
            const grade = parseFloat(gradeText.textContent);
            if (!isNaN(grade)) {
                totalGrades++;
                sumGrades += grade;
                if (grade >= 4.0) {
                    approved++;
                } else {
                    failed++;
                }
            }
        }
    });
    
    return {
        total: totalGrades,
        average: totalGrades > 0 ? (sumGrades / totalGrades).toFixed(1) : '0.0',
        approved: approved,
        failed: failed,
        approvalRate: totalGrades > 0 ? ((approved / totalGrades) * 100).toFixed(0) : '0'
    };
}

// Agregar animación CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);
