/* ===========================
   ASESOR FINANCIERO - INICIO
   inicio.js
   =========================== */

document.addEventListener('DOMContentLoaded', function() {
    cargarKPIs();
    initAnimaciones();
});

// --- Cargar KPIs desde el servidor ---
function cargarKPIs() {
    fetch('/api/asesor-financiero/kpis/')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                actualizarKPIs(data.kpis);
            }
        })
        .catch(error => {
            console.error('Error al cargar KPIs:', error);
        });
}

function actualizarKPIs(kpis) {
    // Total Facturado
    if (kpis.total_facturado !== undefined) {
        animateNumber('totalFacturado', 0, kpis.total_facturado, '$');
    }
    
    // Pagos Recibidos
    if (kpis.pagos_recibidos !== undefined) {
        animateNumber('pagosRecibidos', 0, kpis.pagos_recibidos, '$');
    }
    
    // Saldo Pendiente
    if (kpis.saldo_pendiente !== undefined) {
        animateNumber('saldoPendiente', 0, kpis.saldo_pendiente, '$');
    }
    
    // Cuotas Vencidas
    if (kpis.cuotas_vencidas !== undefined) {
        animateNumber('cuotasVencidas', 0, kpis.cuotas_vencidas, '');
    }
}

// --- Animación de números ---
function animateNumber(elementId, start, end, prefix = '') {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const duration = 1500; // 1.5 segundos
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        
        const current = start + (end - start) * easeOut;
        
        if (prefix === '$') {
            element.textContent = formatCurrency(Math.floor(current));
        } else {
            element.textContent = Math.floor(current);
        }
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

function formatCurrency(value) {
    return '$' + value.toLocaleString('es-CL');
}

// --- Animaciones de entrada ---
function initAnimaciones() {
    // Animar stat cards
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease-out';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
    // Animar module cards
    const moduleCards = document.querySelectorAll('.module-card');
    moduleCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease-out';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 400 + (index * 80));
    });
    
    // Animar alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach((alert, index) => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            alert.style.transition = 'all 0.5s ease-out';
            alert.style.opacity = '1';
            alert.style.transform = 'translateX(0)';
        }, 800 + (index * 100));
    });
}

// --- Actualizar datos en tiempo real (opcional) ---
function startAutoRefresh() {
    // Actualizar KPIs cada 5 minutos
    setInterval(cargarKPIs, 5 * 60 * 1000);
}

// Iniciar actualización automática si se desea
// startAutoRefresh();
