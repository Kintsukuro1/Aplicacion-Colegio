/* ===========================
   MENSAJERÍA APODERADO - JAVASCRIPT
   bandeja.js
   =========================== */

document.addEventListener('DOMContentLoaded', function() {
    initSearch();
    initTabs();
    initConversaciones();
    initChatInput();
    initModal();
    scrollToBottom();
    autoExpandTextarea();
});

// --- Search --- 
function initSearch() {
    const searchInput = document.getElementById('searchConversacion');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        filterConversaciones(searchTerm);
    });
}

function filterConversaciones(searchTerm) {
    const conversaciones = document.querySelectorAll('.conversacion-item');
    let visibleCount = 0;
    
    conversaciones.forEach(item => {
        const nombre = item.querySelector('.conversacion-nombre').textContent.toLowerCase();
        const mensaje = item.querySelector('.conversacion-ultimo-mensaje').textContent.toLowerCase();
        
        if (nombre.includes(searchTerm) || mensaje.includes(searchTerm)) {
            item.style.display = 'flex';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    showEmptyStateIfNeeded(visibleCount);
}

function showEmptyStateIfNeeded(count) {
    const list = document.getElementById('conversacionesList');
    let emptyState = list.querySelector('.empty-state-sidebar');
    
    if (count === 0 && !emptyState) {
        emptyState = document.createElement('div');
        emptyState.className = 'empty-state-sidebar';
        emptyState.innerHTML = `
            <i class="fas fa-search"></i>
            <p>No se encontraron conversaciones</p>
        `;
        list.appendChild(emptyState);
    } else if (count > 0 && emptyState) {
        emptyState.remove();
    }
}

// --- Tabs ---
function initTabs() {
    const tabs = document.querySelectorAll('.tab-button');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Actualizar estado activo
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Filtrar conversaciones
            const tabType = this.dataset.tab;
            filterByTab(tabType);
        });
    });
}

function filterByTab(tabType) {
    const conversaciones = document.querySelectorAll('.conversacion-item');
    let visibleCount = 0;
    
    conversaciones.forEach(item => {
        const esNoLeido = item.dataset.leido === 'false';
        
        if (tabType === 'todos' || (tabType === 'no_leidos' && esNoLeido)) {
            item.style.display = 'flex';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    showEmptyStateIfNeeded(visibleCount);
}

// --- Conversaciones ---
function initConversaciones() {
    const conversaciones = document.querySelectorAll('.conversacion-item');
    
    conversaciones.forEach(item => {
        item.addEventListener('click', function() {
            const conversacionId = this.dataset.id;
            cargarConversacion(conversacionId);
        });
    });
}

function cargarConversacion(conversacionId) {
    // En producción, esto sería una llamada AJAX
    // Por ahora, redirigimos con el ID
    window.location.href = `/mensajeria/?conversacion=${conversacionId}`;
}

// --- Chat Input ---
function initChatInput() {
    const form = document.getElementById('formEnviarMensaje');
    if (!form) return;
    
    const btnAdjuntar = document.querySelector('.btn-adjuntar');
    const inputAdjunto = document.getElementById('inputAdjunto');
    
    if (btnAdjuntar && inputAdjunto) {
        btnAdjuntar.addEventListener('click', () => inputAdjunto.click());
        
        inputAdjunto.addEventListener('change', function() {
            if (this.files.length > 0) {
                showToast(`Archivo seleccionado: ${this.files[0].name}`, 'info');
            }
        });
    }
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        enviarMensaje();
    });
}

function enviarMensaje() {
    const form = document.getElementById('formEnviarMensaje');
    const textarea = document.getElementById('mensajeTexto');
    const contenido = textarea.value.trim();
    
    if (!contenido) {
        showToast('Escribe un mensaje', 'warning');
        return;
    }
    
    const formData = new FormData(form);
    
    fetch('/mensajeria/enviar/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': formData.get('csrfmiddlewaretoken')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Agregar mensaje a la lista
            agregarMensajeAlChat(data.mensaje);
            
            // Limpiar formulario
            textarea.value = '';
            textarea.style.height = 'auto';
            
            // Scroll al final
            scrollToBottom();
            
            showToast('Mensaje enviado', 'success');
        } else {
            showToast(data.message || 'Error al enviar mensaje', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error de conexión', 'error');
    });
}

function agregarMensajeAlChat(mensaje) {
    const chatMensajes = document.getElementById('chatMensajes');
    if (!chatMensajes) return;
    
    const mensajeDiv = document.createElement('div');
    mensajeDiv.className = 'mensaje mensaje-propio';
    
    let adjuntoHTML = '';
    if (mensaje.adjunto) {
        adjuntoHTML = `
            <div class="mensaje-adjunto">
                <i class="fas fa-paperclip"></i>
                <a href="${mensaje.adjunto}" target="_blank">${mensaje.adjunto_nombre}</a>
            </div>
        `;
    }
    
    mensajeDiv.innerHTML = `
        <div class="mensaje-content">
            <div class="mensaje-bubble">
                <p class="mensaje-texto">${mensaje.contenido}</p>
                ${adjuntoHTML}
            </div>
            <span class="mensaje-hora">
                ${mensaje.hora}
                <i class="fas fa-check"></i>
            </span>
        </div>
    `;
    
    chatMensajes.appendChild(mensajeDiv);
}

// --- Auto Expand Textarea ---
function autoExpandTextarea() {
    const textarea = document.getElementById('mensajeTexto');
    if (!textarea) return;
    
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Enter para enviar, Shift+Enter para nueva línea
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.getElementById('formEnviarMensaje').dispatchEvent(new Event('submit'));
        }
    });
}

// --- Scroll to Bottom ---
function scrollToBottom() {
    const chatMensajes = document.getElementById('chatMensajes');
    if (chatMensajes) {
        chatMensajes.scrollTop = chatMensajes.scrollHeight;
    }
}

// --- Modal ---
function initModal() {
    const btnNuevo = document.getElementById('btnNuevoMensaje');
    const modal = document.getElementById('modalNuevoMensaje');
    const btnEnviar = document.getElementById('btnEnviarNuevo');
    const closeBtns = modal.querySelectorAll('[data-dismiss="modal"]');
    
    if (btnNuevo) {
        btnNuevo.addEventListener('click', () => abrirModal());
    }
    
    if (btnEnviar) {
        btnEnviar.addEventListener('click', () => enviarNuevoMensaje());
    }
    
    closeBtns.forEach(btn => {
        btn.addEventListener('click', () => cerrarModal());
    });
    
    // Cerrar con ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            cerrarModal();
        }
    });
    
    // Cerrar al hacer clic fuera
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            cerrarModal();
        }
    });
}

function abrirModal() {
    const modal = document.getElementById('modalNuevoMensaje');
    const form = document.getElementById('formNuevoMensaje');
    
    form.reset();
    modal.classList.add('active');
}

function cerrarModal() {
    const modal = document.getElementById('modalNuevoMensaje');
    modal.classList.remove('active');
}

function enviarNuevoMensaje() {
    const form = document.getElementById('formNuevoMensaje');
    const destinatario = document.getElementById('destinatario').value;
    const mensaje = document.getElementById('mensaje').value.trim();
    
    if (!destinatario) {
        showToast('Selecciona un destinatario', 'warning');
        return;
    }
    
    if (!mensaje) {
        showToast('Escribe un mensaje', 'warning');
        return;
    }
    
    const formData = new FormData(form);
    
    fetch('/mensajeria/nueva/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': formData.get('csrfmiddlewaretoken')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Mensaje enviado', 'success');
            cerrarModal();
            
            // Redirigir a la nueva conversación
            setTimeout(() => {
                window.location.href = `/mensajeria/?conversacion=${data.conversacion_id}`;
            }, 1000);
        } else {
            showToast(data.message || 'Error al enviar mensaje', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error de conexión', 'error');
    });
}

// --- Toast Notifications ---
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// --- WebSocket (Opcional - para mensajes en tiempo real) ---
// Descomentar y configurar cuando implementes WebSocket

/*
let socket;

function initWebSocket() {
    const conversacionId = getConversacionIdFromURL();
    if (!conversacionId) return;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/mensajeria/${conversacionId}/`;
    
    socket = new WebSocket(wsUrl);
    
    socket.onopen = function() {
        console.log('WebSocket conectado');
    };
    
    socket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'nuevo_mensaje') {
            agregarMensajeAlChat(data.mensaje);
            scrollToBottom();
        }
    };
    
    socket.onclose = function() {
        console.log('WebSocket desconectado');
        // Reconectar después de 3 segundos
        setTimeout(initWebSocket, 3000);
    };
    
    socket.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

function getConversacionIdFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('conversacion');
}
*/
