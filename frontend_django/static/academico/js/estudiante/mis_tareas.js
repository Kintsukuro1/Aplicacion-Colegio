/** MIS TAREAS - ESTUDIANTE */

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initTaskAnimations();
});

// Filtrar tareas por estado
function filtrarTareas(estado) {
    const tareas = document.querySelectorAll('.tarea-item, .task-card');
    const tabs = document.querySelectorAll('.tab');
    
    tabs.forEach(tab => {
        if (tab.getAttribute('data-tab') === estado) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    tareas.forEach(tarea => {
        if (estado === 'todas') {
            tarea.style.display = 'block';
        } else if (tarea.getAttribute('data-estado')?.toLowerCase() === estado) {
            tarea.style.display = 'block';
        } else {
            tarea.style.display = 'none';
        }
    });
}

// Filtrar por asignatura
function filtrarPorAsignatura(asignatura) {
    const tareas = document.querySelectorAll('.tarea-item, .task-card');
    
    tareas.forEach(tarea => {
        if (!asignatura || tarea.getAttribute('data-asignatura') === asignatura) {
            tarea.style.display = 'block';
        } else {
            tarea.style.display = 'none';
        }
    });
}

// Ordenar tareas
function ordenarTareas(criterio) {
    console.log('Ordenar por:', criterio);
    const lists = document.querySelectorAll('.tareas-lista');
    lists.forEach(list => {
        const cards = Array.from(list.querySelectorAll('.tarea-card'));
        if (cards.length === 0) return;
        
        cards.sort((a, b) => {
            if (criterio === 'fecha') {
                const textA = a.querySelector('.meta-item')?.textContent.replace('Vence:', '').replace('Vencimiento:', '').trim() || '';
                const textB = b.querySelector('.meta-item')?.textContent.replace('Vence:', '').replace('Vencimiento:', '').trim() || '';
                // Parse date from DD/MM/YYYY
                const parseDate = (str) => {
                    const parts = str.split(' ')[0].split('/');
                    if (parts.length < 3) return new Date(0);
                    return new Date(parts[2], parts[1] - 1, parts[0]);
                };
                return parseDate(textA) - parseDate(textB);
            } else if (criterio === 'titulo') {
                const titleA = a.querySelector('.title-primary')?.textContent.trim() || '';
                const titleB = b.querySelector('.title-primary')?.textContent.trim() || '';
                return titleA.localeCompare(titleB);
            } else if (criterio === 'asignatura') {
                const asigA = a.querySelector('.tarea-badge')?.textContent.trim() || '';
                const asigB = b.querySelector('.tarea-badge')?.textContent.trim() || '';
                return asigA.localeCompare(asigB);
            }
            return 0;
        });
        
        cards.forEach(card => list.appendChild(card));
    });
    
    if (typeof ToastManager !== 'undefined') {
        ToastManager.success(`Tareas ordenadas por ${criterio}`);
    }
}

// Ver detalle de tarea
function verDetalleTarea(tareaId) {
    console.log('Ver tarea:', tareaId);
    // Expand description area in the task card if available
    const cards = document.querySelectorAll('.tarea-card');
    cards.forEach(card => {
        // Simple mock of detail lookup or expand
        const title = card.querySelector('.title-primary')?.textContent.trim() || '';
        if (title.toLowerCase().includes('tarea') || true) {
            let desc = card.querySelector('.tarea-desc-extend');
            if (!desc) {
                desc = document.createElement('div');
                desc.className = 'tarea-desc-extend';
                desc.style.padding = '12px';
                desc.style.marginTop = '12px';
                desc.style.background = '#f8fafc';
                desc.style.borderTop = '1px solid #e2e8f0';
                desc.style.borderRadius = '0 0 8px 8px';
                desc.style.fontSize = '0.9rem';
                desc.style.color = '#475569';
                desc.innerHTML = `<strong>Guía de Actividades:</strong> Sigue las instrucciones del docente. Resuelve los ejercicios propuestos en tu cuaderno o computadora y sube tu entrega en formato PDF o ZIP antes de la fecha límite.`;
                card.appendChild(desc);
            } else {
                desc.style.display = desc.style.display === 'none' ? 'block' : 'none';
            }
        }
    });
}

// Entregar tarea
function entregarTarea(tareaId, titulo = '') {
    const modal = document.getElementById('modalEntrega');
    if (modal) {
        document.getElementById('tarea_id').value = tareaId;
        document.getElementById('tareaTituloMuestra').textContent = 'Tarea: ' + titulo;
        modal.style.display = 'flex';
    } else {
        const modalCustom = document.getElementById('modal-entregar-custom');
        if (modalCustom) {
            document.getElementById('tarea-id').value = tareaId;
            modalCustom.style.display = 'flex';
        }
    }
}

// Cerrar modal
function cerrarModalEntregar() {
    const modal = document.getElementById('modalEntrega') || document.getElementById('modal-entregar-custom');
    if (modal) {
        modal.style.display = 'none';
    }
    const form = document.getElementById('formEntrega') || document.getElementById('form-entregar-tarea');
    if (form) {
        form.reset();
    }
}

// Submit entrega via AJAX
function submitEntrega() {
    const form = document.getElementById('formEntrega') || document.getElementById('form-entregar-tarea');
    if (!form) return;

    if (form.checkValidity()) {
        const btn = document.getElementById('btnEnviar') || form.querySelector('button[type="submit"]');
        const originalText = btn ? btn.textContent : 'Subir Entrega';
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Enviando...';
        }

        const formData = new FormData(form);

        fetch('/api/estudiante/tareas/entregar/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken') || getCsrfToken()
            },
            body: formData
        })
        .then(r => r.json())
        .then(data => {
            if (data.success || data.status === 'success') {
                if (typeof ToastManager !== 'undefined') {
                    ToastManager.success('¡Tarea entregada exitosamente!');
                } else {
                    alert('¡Tarea entregada exitosamente!');
                }
                cerrarModalEntregar();
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                alert(data.error || 'Error al enviar la tarea');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            }
        })
        .catch(() => {
            alert('Error de red al entregar la tarea');
            if (btn) {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });
    } else {
        form.reportValidity();
    }
}

function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Inicializar tabs
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            filtrarTareas(tabName);
        });
    });
}

// Animación de entrada para tareas
function initTaskAnimations() {
    const tareas = document.querySelectorAll('.tarea-item, .task-card');
    tareas.forEach((tarea, index) => {
        tarea.style.opacity = '0';
        tarea.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            tarea.style.transition = 'all 0.3s ease';
            tarea.style.opacity = '1';
            tarea.style.transform = 'translateY(0)';
        }, index * 50);
    });
}
