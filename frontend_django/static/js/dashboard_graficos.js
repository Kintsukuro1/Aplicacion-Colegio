/**
 * Dashboard de Gráficos Interactivos
 * Sistema de visualización de estadísticas con Chart.js
 */

// Configuración global de Chart.js
Chart.defaults.font.family = "'Inter', 'Segoe UI', sans-serif";
Chart.defaults.color = '#64748b';
Chart.defaults.plugins.legend.display = true;
Chart.defaults.plugins.legend.position = 'bottom';

// Variables globales para instancias de gráficos
let asistenciaChart = null;
let calificacionesChart = null;
let rendimientoChart = null;
let tendenciaChart = null;

// Colores del tema
const COLORS = {
    primary: '#3b82f6',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#06b6d4',
    purple: '#8b5cf6',
    gradient: ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
};

/**
 * Inicialización al cargar el DOM
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Dashboard Gráficos] Inicializando...');

    // Cargar estadísticas rápidas
    cargarEstadisticasRapidas();

    // Cargar gráficos
    inicializarGraficoAsistencia();
    inicializarGraficoCalificaciones();
    inicializarGraficoRendimiento();
    inicializarGraficoTendencia();
});

/**
 * Cargar estadísticas rápidas (cards superiores)
 */
async function cargarEstadisticasRapidas() {
    try {
        const response = await fetch('/api/dashboard/estadisticas/');
        const data = await response.json();

        const container = document.getElementById('statsSummary');
        container.innerHTML = '';

        // Configuración de cards según datos recibidos
        const statsConfig = generarConfiguracionStats(data);

        statsConfig.forEach(stat => {
            const card = document.createElement('div');
            card.className = 'stat-card';
            card.innerHTML = `
                <span class="icon">${stat.icon}</span>
                <div class="label">${stat.label}</div>
                <div class="value">
                    ${stat.value}
                    ${stat.unit ? `<span class="unit">${stat.unit}</span>` : ''}
                </div>
            `;
            container.appendChild(card);
        });

    } catch (error) {
        console.error('[Dashboard Gráficos] Error cargando estadísticas:', error);
        mostrarError('statsSummary', 'No se pudieron cargar las estadísticas');
    }
}

/**
 * Generar configuración de stats según el rol
 */
function generarConfiguracionStats(data) {
    // Estudiante
    if (data.promedio_general !== undefined) {
        return [
            { icon: '📊', label: 'Promedio General', value: data.promedio_general, unit: '' },
            { icon: '✅', label: 'Asistencia', value: data.asistencia_porcentaje, unit: '%' },
            { icon: '📝', label: 'Tareas Pendientes', value: data.tareas_pendientes, unit: '' },
            { icon: '📅', label: 'Evaluaciones Próximas', value: data.evaluaciones_proximas, unit: '' },
        ];
    }
    // Profesor
    if (data.total_clases !== undefined) {
        return [
            { icon: '📚', label: 'Total Clases', value: data.total_clases, unit: '' },
            { icon: '👥', label: 'Total Estudiantes', value: data.total_estudiantes, unit: '' },
            { icon: '📊', label: 'Promedio Clases', value: data.promedio_clases, unit: '' },
            { icon: '✅', label: 'Asistencia Promedio', value: data.asistencia_promedio, unit: '%' },
        ];
    }
    // Admin
    if (data.total_estudiantes !== undefined) {
        return [
            { icon: '👨‍🎓', label: 'Total Estudiantes', value: data.total_estudiantes, unit: '' },
            { icon: '👩‍🏫', label: 'Total Profesores', value: data.total_profesores, unit: '' },
            { icon: '🏫', label: 'Total Cursos', value: data.total_cursos, unit: '' },
            { icon: '📊', label: 'Promedio General', value: data.promedio_general, unit: '' },
        ];
    }

    return [
        { icon: '📊', label: 'Sin datos', value: '--', unit: '' }
    ];
}

/**
 * Gráfico 1: Asistencia Mensual (Línea)
 */
async function inicializarGraficoAsistencia() {
    try {
        const response = await fetch('/api/dashboard/asistencia/');
        const data = await response.json();

        const ctx = document.getElementById('asistenciaChart').getContext('2d');

        // Destruir gráfico anterior si existe
        if (asistenciaChart) {
            asistenciaChart.destroy();
        }

        asistenciaChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Asistencia (%)',
                    data: data.data,
                    borderColor: COLORS.primary,
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: COLORS.primary,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        callbacks: {
                            label: function(context) {
                                return `${context.parsed.y}% de asistencia`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('[Dashboard Gráficos] Error en gráfico de asistencia:', error);
        mostrarErrorEnCanvas('asistenciaChart', 'Error al cargar datos de asistencia');
    }
}

/**
 * Gráfico 2: Calificaciones por Asignatura (Barras)
 */
async function inicializarGraficoCalificaciones() {
    try {
        const response = await fetch('/api/dashboard/calificaciones/');
        const data = await response.json();

        const ctx = document.getElementById('calificacionesChart').getContext('2d');

        if (calificacionesChart) {
            calificacionesChart.destroy();
        }

        calificacionesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Promedio',
                    data: data.data,
                    backgroundColor: COLORS.gradient,
                    borderRadius: 8,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        callbacks: {
                            label: function(context) {
                                return `Promedio: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 7.0,
                        ticks: {
                            stepSize: 1.0
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('[Dashboard Gráficos] Error en gráfico de calificaciones:', error);
        mostrarErrorEnCanvas('calificacionesChart', 'Error al cargar calificaciones');
    }
}

/**
 * Gráfico 3: Distribución de Rendimiento (Dona)
 */
async function inicializarGraficoRendimiento() {
    try {
        const response = await fetch('/api/dashboard/rendimiento/');
        const data = await response.json();

        const ctx = document.getElementById('rendimientoChart').getContext('2d');

        if (rendimientoChart) {
            rendimientoChart.destroy();
        }

        rendimientoChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.data,
                    backgroundColor: [
                        COLORS.danger,
                        COLORS.warning,
                        COLORS.info,
                        COLORS.success
                    ],
                    borderWidth: 3,
                    borderColor: '#fff',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'right',
                        labels: {
                            padding: 15,
                            font: { size: 12 },
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const porcentaje = total ? ((context.parsed / total) * 100).toFixed(1) : '0.0';
                                return `${context.label}: ${context.parsed} (${porcentaje}%)`;
                            }
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('[Dashboard Gráficos] Error en gráfico de rendimiento:', error);
        mostrarErrorEnCanvas('rendimientoChart', 'Error al cargar distribución');
    }
}

/**
 * Gráfico 4: Tendencia de Rendimiento (Línea suavizada)
 */
async function inicializarGraficoTendencia() {
    try {
        // Reutilizar datos de asistencia para mostrar tendencia
        const response = await fetch('/api/dashboard/asistencia/');
        const data = await response.json();

        const ctx = document.getElementById('tendenciaChart').getContext('2d');

        if (tendenciaChart) {
            tendenciaChart.destroy();
        }

        tendenciaChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Tendencia',
                    data: data.data,
                    borderColor: COLORS.success,
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: COLORS.success,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('[Dashboard Gráficos] Error en gráfico de tendencia:', error);
        mostrarErrorEnCanvas('tendenciaChart', 'Error al cargar tendencia');
    }
}

/**
 * Mostrar error en un contenedor
 */
function mostrarError(containerId, mensaje) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="error-message">
                <strong>❌ Error:</strong> ${mensaje}
            </div>
        `;
    }
}

/**
 * Mostrar error en un canvas
 */
function mostrarErrorEnCanvas(canvasId, mensaje) {
    const canvas = document.getElementById(canvasId);
    if (canvas) {
        const parent = canvas.parentElement;
        parent.innerHTML = `
            <div class="error-message" style="margin: 20px;">
                <strong>❌ Error:</strong> ${mensaje}
            </div>
        `;
    }
}

/**
 * Actualizar todos los gráficos (útil para refrescar datos)
 */
function actualizarGraficos() {
    console.log('[Dashboard Gráficos] Actualizando todos los gráficos...');
    cargarEstadisticasRapidas();
    inicializarGraficoAsistencia();
    inicializarGraficoCalificaciones();
    inicializarGraficoRendimiento();
    inicializarGraficoTendencia();
}

// Exponer función global para actualización manual
window.actualizarDashboardGraficos = actualizarGraficos;

console.log('[Dashboard Gráficos] Script cargado correctamente');
