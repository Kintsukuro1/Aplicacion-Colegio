/**
 * PERFIL - APODERADO
 * Gestión del perfil de apoderado
 */

document.addEventListener('DOMContentLoaded', function() {
    initPerfilApoderado();
});

/**
 * Inicializa la funcionalidad del perfil
 */
function initPerfilApoderado() {
    initTabs();
    initPasswordValidation();
    initCardsAnimation();
    
    console.log('Perfil de apoderado inicializado');
}

/**
 * Inicializa el sistema de tabs
 */
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remover active de todos los tabs
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(content => {
                content.classList.remove('active');
                content.style.display = 'none';
            });
            
            // Activar el tab clickeado
            this.classList.add('active');
            const targetContent = document.getElementById(`${targetTab}-tab`);
            if (targetContent) {
                targetContent.classList.add('active');
                targetContent.style.display = 'block';
                
                // Animar entrada
                targetContent.style.opacity = '0';
                targetContent.style.transform = 'translateY(10px)';
                
                setTimeout(() => {
                    targetContent.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    targetContent.style.opacity = '1';
                    targetContent.style.transform = 'translateY(0)';
                }, 10);
            }
        });
    });
}

/**
 * Inicializa la validación de contraseña
 */
function initPasswordValidation() {
    const passwordNueva = document.getElementById('password_nueva');
    const passwordConfirmar = document.getElementById('password_confirmar');
    const messageElement = document.getElementById('password-match-message');
    
    if (!passwordNueva || !passwordConfirmar || !messageElement) return;
    
    function validatePasswords() {
        const nueva = passwordNueva.value;
        const confirmar = passwordConfirmar.value;
        
        if (confirmar === '') {
            messageElement.textContent = '';
            messageElement.className = 'form-help';
            return;
        }
        
        if (nueva === confirmar) {
            messageElement.textContent = '✓ Las contraseñas coinciden';
            messageElement.className = 'form-help success';
        } else {
            messageElement.textContent = '✗ Las contraseñas no coinciden';
            messageElement.className = 'form-help error';
        }
    }
    
    passwordNueva.addEventListener('input', validatePasswords);
    passwordConfirmar.addEventListener('input', validatePasswords);
    
    // Validar fortaleza de contraseña
    passwordNueva.addEventListener('input', function() {
        const password = this.value;
        const strength = calculatePasswordStrength(password);
        
        // Aquí podrías mostrar un indicador visual de fortaleza
        console.log('Fortaleza de contraseña:', strength);
    });
}

/**
 * Calcula la fortaleza de una contraseña
 * @param {string} password - Contraseña a evaluar
 * @returns {string} Nivel de fortaleza (débil, media, fuerte)
 */
function calculatePasswordStrength(password) {
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    
    if (strength <= 2) return 'débil';
    if (strength <= 4) return 'media';
    return 'fuerte';
}

/**
 * Resetea el formulario de seguridad
 */
function resetSeguridadForm() {
    const form = document.getElementById('formSeguridad');
    if (form) {
        form.reset();
        
        const messageElement = document.getElementById('password-match-message');
        if (messageElement) {
            messageElement.textContent = '';
            messageElement.className = 'form-help';
        }
    }
}

/**
 * Anima la aparición de las cards
 */
function initCardsAnimation() {
    // Animar sidebar cards
    const sidebarCards = document.querySelectorAll('.perfil-sidebar .card');
    sidebarCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateX(0)';
        }, index * 100);
    });
    
    // Animar main content
    const mainCards = document.querySelectorAll('.perfil-main > *');
    mainCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 200 + (index * 100));
    });
}

/**
 * Valida un formulario antes de enviarlo
 * @param {Event} event - Evento de submit del formulario
 */
function validarFormulario(event) {
    const form = event.target;
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.style.borderColor = 'var(--danger-color)';
            
            setTimeout(() => {
                input.style.borderColor = '';
            }, 2000);
        }
    });
    
    if (!isValid) {
        event.preventDefault();
        showToast('Por favor complete todos los campos requeridos', 'error');
    }
}

/**
 * Previsualiza una imagen antes de subirla
 * @param {File} file - Archivo de imagen
 */
function previsualizarImagen(file) {
    if (!file || !file.type.startsWith('image/')) return;
    
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const avatar = document.querySelector('.avatar-xl');
        if (avatar) {
            avatar.style.backgroundImage = `url(${e.target.result})`;
            avatar.style.backgroundSize = 'cover';
            avatar.style.backgroundPosition = 'center';
            avatar.textContent = '';
        }
    };
    
    reader.readAsDataURL(file);
}

/**
 * Muestra notificación toast
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo de notificación (success, error, info, warning)
 */
function showToast(message, type = 'info') {
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        info: '#3b82f6',
        warning: '#f59e0b'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        padding: 1rem 1.5rem;
        background: ${colors[type] || colors.info};
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

// Agregar validación a los formularios
document.querySelectorAll('.profile-form').forEach(form => {
    form.addEventListener('submit', validarFormulario);
});
