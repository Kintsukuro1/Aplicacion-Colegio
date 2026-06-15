/**
 * Gráfico doughnut de asistencia (admin escolar / profesor).
 */
(function () {
    'use strict';

    var lastChartKey = null;

    function initAsistenciaChart() {
        var canvas = document.getElementById('asistenciaChart');
        if (!canvas || typeof Chart === 'undefined') return;

        var chartKey = canvas.getAttribute('data-chart-key') || '';
        var presentes = parseInt(canvas.getAttribute('data-presentes') || '0', 10);
        var ausentes = parseInt(canvas.getAttribute('data-ausentes') || '0', 10);
        var tardanzas = parseInt(canvas.getAttribute('data-tardanzas') || '0', 10);
        var justificadas = parseInt(canvas.getAttribute('data-justificadas') || '0', 10);
        var total = presentes + ausentes + tardanzas + justificadas;

        if (total <= 0) return;

        if (canvas.chartInstance && lastChartKey === chartKey) {
            return;
        }

        if (canvas.chartInstance) {
            canvas.chartInstance.destroy();
            canvas.chartInstance = null;
        }

        lastChartKey = chartKey;

        canvas.chartInstance = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Presentes', 'Ausentes', 'Atrasos', 'Justificadas'],
                datasets: [{
                    data: [presentes, ausentes, tardanzas, justificadas],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#3b82f6'],
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 450
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            font: { family: "'Inter', sans-serif", size: 11 },
                            color: '#5b21b6',
                            boxWidth: 10,
                            padding: 12
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                var label = context.label || '';
                                var value = context.parsed;
                                var sum = context.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                                var pct = sum > 0 ? Math.round((value / sum) * 100) : 0;
                                return label + ': ' + value + ' (' + pct + '%)';
                            }
                        }
                    }
                },
                cutout: '68%'
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAsistenciaChart);
    } else {
        initAsistenciaChart();
    }
})();
