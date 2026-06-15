/* ===========================
   ASESOR FINANCIERO - DASHBOARD
   dashboard.js
   =========================== */

let charts = {};

document.addEventListener('DOMContentLoaded', function() {
    initFiltros();
    cargarDatos();
    initCharts();
});

// --- Filtros ---
function initFiltros() {
    const periodoSelect = document.getElementById('periodoSelect');
    const filtrosPersonalizados = document.querySelectorAll('.filtro-personalizado');
    const btnAplicar = document.getElementById('btnAplicarFiltros');
    const btnActualizar = document.getElementById('btnActualizar');
    
    periodoSelect.addEventListener('change', function() {
        if (this.value === 'personalizado') {
            filtrosPersonalizados.forEach(f => f.style.display = 'flex');
        } else {
            filtrosPersonalizados.forEach(f => f.style.display = 'none');
        }
    });
    
    btnAplicar.addEventListener('click', () => cargarDatos());
    btnActualizar.addEventListener('click', () => cargarDatos());
}

// --- Cargar Datos ---
function cargarDatos() {
    const periodo = document.getElementById('periodoSelect').value;
    let fechaInicio = null;
    let fechaFin = null;
    
    if (periodo === 'personalizado') {
        fechaInicio = document.getElementById('fechaInicio').value;
        fechaFin = document.getElementById('fechaFin').value;
    }
    
    const params = new URLSearchParams({
        periodo: periodo,
        ...(fechaInicio && { fecha_inicio: fechaInicio }),
        ...(fechaFin && { fecha_fin: fechaFin })
    });
    
    fetch(`/api/asesor-financiero/dashboard/?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                actualizarKPIs(data.kpis);
                actualizarGraficos(data.graficos);
                actualizarTablaResumen(data.resumen_niveles);
            }
        })
        .catch(error => console.error('Error:', error));
}

// --- KPIs ---
function actualizarKPIs(kpis) {
    animateValue('kpiIngresosTotales', kpis.ingresos_totales, '$');
    animateValue('kpiTasaCobro', kpis.tasa_cobro, '%');
    animateValue('kpiSaldoPendiente', kpis.saldo_pendiente, '$');
    animateValue('kpiMorosidad', kpis.morosidad, '%');
    
    // Detalles
    document.getElementById('kpiIngresosChange').innerHTML = 
        `<i class="fas fa-arrow-${kpis.ingresos_cambio >= 0 ? 'up' : 'down'}"></i> ${kpis.ingresos_cambio}% vs periodo anterior`;
    document.getElementById('kpiIngresosChange').className = 
        `kpi-change ${kpis.ingresos_cambio >= 0 ? 'positive' : 'negative'}`;
    
    document.getElementById('kpiCobroDetail').textContent = 
        `${kpis.cuotas_cobradas} de ${kpis.cuotas_totales} cuotas cobradas`;
    document.getElementById('kpiPendienteDetail').textContent = 
        `${kpis.estudiantes_pendientes} estudiantes`;
    document.getElementById('kpiMorosidadDetail').textContent = 
        `$${formatNumber(kpis.monto_morosidad)} en cuotas vencidas`;
}

function animateValue(id, value, suffix = '') {
    const element = document.getElementById(id);
    const duration = 1000;
    const start = 0;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = start + (value - start) * progress;
        
        if (suffix === '$') {
            element.textContent = '$' + formatNumber(Math.floor(current));
        } else if (suffix === '%') {
            element.textContent = current.toFixed(1) + '%';
        } else {
            element.textContent = Math.floor(current);
        }
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// --- Gráficos ---
function initCharts() {
    // Configuración por defecto
    Chart.defaults.font.family = 'system-ui, -apple-system, sans-serif';
    Chart.defaults.color = '#6b7280';
}

function actualizarGraficos(graficos) {
    // Ingresos Mensuales (Línea)
    createOrUpdateChart('chartIngresosMensuales', 'line', {
        labels: graficos.ingresos_mensuales.labels,
        datasets: [{
            label: 'Ingresos',
            data: graficos.ingresos_mensuales.data,
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99, 102, 241, 0.1)',
            tension: 0.4,
            fill: true
        }]
    });
    
    // Ingresos por Curso (Dona)
    createOrUpdateChart('chartIngresosCurso', 'doughnut', {
        labels: graficos.ingresos_curso.labels,
        datasets: [{
            data: graficos.ingresos_curso.data,
            backgroundColor: [
                '#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', 
                '#10b981', '#3b82f6', '#ef4444', '#06b6d4'
            ]
        }]
    });
    
    // Estado de Cuotas (Barra)
    createOrUpdateChart('chartEstadoCuotas', 'bar', {
        labels: graficos.estado_cuotas.labels,
        datasets: [{
            label: 'Cuotas',
            data: graficos.estado_cuotas.data,
            backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#6b7280']
        }]
    });
    
    // Métodos de Pago (Torta)
    createOrUpdateChart('chartMetodosPago', 'pie', {
        labels: graficos.metodos_pago.labels,
        datasets: [{
            data: graficos.metodos_pago.data,
            backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#8b5cf6']
        }]
    });
    
    // Top Morosos (Barra Horizontal)
    createOrUpdateChart('chartTopMorosos', 'bar', {
        labels: graficos.top_morosos.labels,
        datasets: [{
            label: 'Deuda',
            data: graficos.top_morosos.data,
            backgroundColor: '#ef4444'
        }]
    }, {
        indexAxis: 'y',
        scales: {
            x: {
                ticks: {
                    callback: value => '$' + formatNumber(value)
                }
            }
        }
    });
}

function createOrUpdateChart(canvasId, type, data, extraOptions = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }
    
    charts[canvasId] = new Chart(ctx, {
        type: type,
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            },
            ...extraOptions
        }
    });
}

// --- Tabla Resumen ---
function actualizarTablaResumen(niveles) {
    const tbody = document.querySelector('#tablaResumenNiveles tbody');
    tbody.innerHTML = '';
    
    let totales = {
        estudiantes: 0,
        facturado: 0,
        cobrado: 0,
        pendiente: 0,
        morosidad: 0
    };
    
    niveles.forEach(nivel => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${nivel.nombre}</strong></td>
            <td>${nivel.estudiantes}</td>
            <td>$${formatNumber(nivel.facturado)}</td>
            <td>$${formatNumber(nivel.cobrado)}</td>
            <td>$${formatNumber(nivel.pendiente)}</td>
            <td>${nivel.porcentaje_cobro}%</td>
            <td>$${formatNumber(nivel.morosidad)}</td>
        `;
        tbody.appendChild(tr);
        
        totales.estudiantes += nivel.estudiantes;
        totales.facturado += nivel.facturado;
        totales.cobrado += nivel.cobrado;
        totales.pendiente += nivel.pendiente;
        totales.morosidad += nivel.morosidad;
    });
    
    // Actualizar totales
    document.getElementById('totalEstudiantes').textContent = totales.estudiantes;
    document.getElementById('totalFacturado').textContent = '$' + formatNumber(totales.facturado);
    document.getElementById('totalCobrado').textContent = '$' + formatNumber(totales.cobrado);
    document.getElementById('totalPendiente').textContent = '$' + formatNumber(totales.pendiente);
    document.getElementById('totalPorcentajeCobro').textContent = 
        ((totales.cobrado / totales.facturado) * 100).toFixed(1) + '%';
    document.getElementById('totalMorosidad').textContent = '$' + formatNumber(totales.morosidad);
}

// --- Utilidades ---
function formatNumber(num) {
    return Math.floor(num).toLocaleString('es-CL');
}

// --- Exportar ---
document.getElementById('btnExportar')?.addEventListener('click', function() {
    const periodo = document.getElementById('periodoSelect').value;
    window.location.href = `/api/asesor-financiero/dashboard/exportar/?periodo=${periodo}`;
});
