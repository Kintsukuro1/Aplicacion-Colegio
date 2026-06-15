/**
 * REPORTE ASISTENCIA - JAVASCRIPT
 * Scripts para el reporte de asistencia (admin_escolar)
 */

document.addEventListener('DOMContentLoaded', function() {
    initFiltros();
    initGrafico();
    initTablaSearch();
    initExport();
});

/**
 * Inicializa los filtros
 */
function initFiltros() {
    const formFiltros = document.getElementById('formFiltros');
    const periodSelect = document.getElementById('periodo');
    const grupoFechaInicio = document.getElementById('grupoFechaInicio');
    const grupoFechaFin = document.getElementById('grupoFechaFin');
    const btnLimpiar = document.getElementById('btnLimpiarFiltros');
    
    // Mostrar/ocultar campos de fecha personalizada
    if (periodSelect) {
        periodSelect.addEventListener('change', function() {
            const esPersonalizado = this.value === 'personalizado';
            if (grupoFechaInicio) grupoFechaInicio.style.display = esPersonalizado ? 'block' : 'none';
            if (grupoFechaFin) grupoFechaFin.style.display = esPersonalizado ? 'block' : 'none';
        });
    }
    
    // Submit del formulario
    if (formFiltros) {
        formFiltros.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validar fechas si es personalizado
            if (periodSelect.value === 'personalizado') {
                const fechaInicio = document.getElementById('fecha_inicio').value;
                const fechaFin = document.getElementById('fecha_fin').value;
                
                if (!fechaInicio || !fechaFin) {
                    showToast('Debes seleccionar ambas fechas para el período personalizado', 'warning');
                    return;
                }
                
                if (new Date(fechaInicio) > new Date(fechaFin)) {
                    showToast('La fecha de inicio no puede ser posterior a la fecha de fin', 'error');
                    return;
                }
            }
            
            // Enviar formulario
            this.submit();
        });
    }
    
    // Limpiar filtros
    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', function() {
            window.location.href = window.location.pathname;
        });
    }
}

/**
 * Inicializa el gráfico de asistencia
 */
function initGrafico() {
    const canvas = document.getElementById('graficoAsistencia');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Validar que existan datos
    if (typeof datosGrafico === 'undefined' || !datosGrafico.labels || datosGrafico.labels.length === 0) {
        canvas.parentElement.innerHTML = '<p class="empty-message">No hay datos para mostrar en el gráfico</p>';
        return;
    }
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: datosGrafico.labels,
            datasets: [
                {
                    label: 'Presentes',
                    data: datosGrafico.presentes,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Ausentes',
                    data: datosGrafico.ausentes,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Atrasos',
                    data: datosGrafico.atrasos,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 13,
                            family: "'Inter', sans-serif"
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: '600'
                    },
                    bodyFont: {
                        size: 13
                    },
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    ticks: {
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
    
    // Botón refresh
    const btnRefresh = document.getElementById('btnRefreshGrafico');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', function() {
            this.querySelector('i').classList.add('fa-spin');
            chart.update();
            setTimeout(() => {
                this.querySelector('i').classList.remove('fa-spin');
            }, 500);
        });
    }
}

/**
 * Inicializa la búsqueda en la tabla
 */
function initTablaSearch() {
    const searchInput = document.getElementById('searchCurso');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        const rows = document.querySelectorAll('.curso-row');
        
        rows.forEach(row => {
            const cursoNombre = row.dataset.curso;
            if (cursoNombre.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
}

/**
 * Inicializa los botones de exportación
 */
function initExport() {
    const btnExportarPDF = document.getElementById('btnExportarPDF');
    const btnExportarExcel = document.getElementById('btnExportarExcel');
    
    if (btnExportarPDF) {
        btnExportarPDF.addEventListener('click', function() {
            exportar('pdf');
        });
    }
    
    if (btnExportarExcel) {
        btnExportarExcel.addEventListener('click', function() {
            exportar('excel');
        });
    }
}

/**
 * Exporta el reporte
 * @param {string} formato - 'pdf' o 'excel'
 */
function exportar(formato) {
    // Obtener parámetros actuales
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.set('formato', formato);
    
    // Construir URL de exportación
    const exportUrl = window.location.pathname + 'exportar/?' + urlParams.toString();
    
    // Mostrar mensaje de descarga
    showToast(`Preparando descarga en formato ${formato.toUpperCase()}...`, 'info');
    
    // Abrir en nueva ventana
    window.open(exportUrl, '_blank');
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
