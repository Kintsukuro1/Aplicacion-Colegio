/**
 * PERFIL ADMIN - JAVASCRIPT
 * Scripts para el perfil de administradores
 */

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initPasswordValidation();
    initPasswordToggle();
    initAvatarUpload();
    initForms();
});

/**
 * Inicializa el sistema de pestañas
 */
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;
            
            // Remover clases activas
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Agregar clases activas
            tab.classList.add('active');
            const targetContent = document.getElementById(`tab-${targetTab}`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
}

/**
 * Inicializa la validación de contraseña
 */
function initPasswordValidation() {
    const passwordNuevaInput = document.getElementById('password_nueva');
    const passwordConfirmarInput = document.getElementById('password_confirmar');
    
    if (!passwordNuevaInput) return;
    
    passwordNuevaInput.addEventListener('input', function() {
        const strength = calculatePasswordStrength(this.value);
        updatePasswordStrengthUI(strength);
    });
    
    if (passwordConfirmarInput) {
        passwordConfirmarInput.addEventListener('input', function() {
            validatePasswordMatch();
        });
    }
}

/**
 * Calcula la fortaleza de la contraseña
 * @param {string} password - Contraseña a evaluar
 * @returns {string} 'debil', 'media' o 'fuerte'
 */
function calculatePasswordStrength(password) {
    let strength = 0;
    
    // Longitud
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    
    // Mayúsculas
    if (/[A-Z]/.test(password)) strength++;
    
    // Minúsculas
    if (/[a-z]/.test(password)) strength++;
    
    // Números
    if (/[0-9]/.test(password)) strength++;
    
    // Caracteres especiales
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    
    if (strength <= 2) return 'debil';
    if (strength <= 4) return 'media';
    return 'fuerte';
}

/**
 * Actualiza la UI de fortaleza de contraseña
 * @param {string} strength - Nivel de fortaleza
 */
function updatePasswordStrengthUI(strength) {
    const strengthBar = document.querySelector('.strength-bar-fill');
    const strengthText = document.querySelector('.strength-text');
    
    if (!strengthBar || !strengthText) return;
    
    // Remover clases anteriores
    strengthBar.className = 'strength-bar-fill';
    strengthText.className = 'strength-text';
    
    // Agregar nueva clase
    strengthBar.classList.add(strength);
    strengthText.classList.add(strength);
    
    // Actualizar texto
    const textos = {
        debil: 'Contraseña débil',
        media: 'Contraseña media',
        fuerte: 'Contraseña fuerte'
    };
    strengthText.textContent = textos[strength];
}

/**
 * Valida que las contraseñas coincidan
 */
function validatePasswordMatch() {
    const passwordNueva = document.getElementById('password_nueva');
    const passwordConfirmar = document.getElementById('password_confirmar');
    
    if (!passwordNueva || !passwordConfirmar) return;
    
    const match = passwordNueva.value === passwordConfirmar.value;
    
    if (passwordConfirmar.value.length > 0) {
        if (match) {
            passwordConfirmar.setCustomValidity('');
            passwordConfirmar.style.borderColor = 'var(--success-color)';
        } else {
            passwordConfirmar.setCustomValidity('Las contraseñas no coinciden');
            passwordConfirmar.style.borderColor = 'var(--danger-color)';
        }
    } else {
        passwordConfirmar.setCustomValidity('');
        passwordConfirmar.style.borderColor = '';
    }
}

/**
 * Inicializa los botones de mostrar/ocultar contraseña
 */
function initPasswordToggle() {
    const toggleButtons = document.querySelectorAll('.btn-toggle-password');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.dataset.target;
            const input = document.getElementById(targetId);
            const icon = this.querySelector('i');
            
            if (!input || !icon) return;
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
}

/**
 * Inicializa la carga de avatar
 */
function initAvatarUpload() {
    const btnCambiarAvatar = document.getElementById('btnCambiarAvatar');
    const inputAvatar = document.getElementById('inputAvatar');
    
    if (!btnCambiarAvatar || !inputAvatar) return;
    
    btnCambiarAvatar.addEventListener('click', () => {
        inputAvatar.click();
    });
    
    inputAvatar.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const file = this.files[0];
            
            // Validar tamaño (máximo 2MB)
            if (file.size > 2 * 1024 * 1024) {
                showToast('La imagen no puede superar los 2MB', 'error');
                return;
            }
            
            // Validar tipo
            if (!file.type.startsWith('image/')) {
                showToast('El archivo debe ser una imagen', 'error');
                return;
            }
            
            // Previsualizar imagen
            const reader = new FileReader();
            reader.onload = function(e) {
                const avatarImg = document.querySelector('.avatar-xl');
                if (avatarImg.tagName === 'IMG') {
                    avatarImg.src = e.target.result;
                } else {
                    // Reemplazar placeholder con img
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    img.alt = 'Avatar';
                    img.className = 'avatar-xl';
                    avatarImg.parentNode.replaceChild(img, avatarImg);
                }
                
                // Subir imagen al servidor
                uploadAvatar(file);
            };
            reader.readAsDataURL(file);
        }
    });
}

/**
 * Sube el avatar al servidor
 * @param {File} file - Archivo de imagen
 */
function uploadAvatar(file) {
    const formData = new FormData();
    formData.append('foto', file);
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    
    fetch(window.location.pathname, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Avatar actualizado correctamente', 'success');
        } else {
            showToast(data.message || 'Error al actualizar avatar', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error al subir la imagen', 'error');
    });
}

/**
 * Inicializa los formularios
 */
function initForms() {
    const forms = [
        { id: 'formPersonal', endpoint: 'update_personal' },
        { id: 'formContacto', endpoint: 'update_contacto' },
        { id: 'formSeguridad', endpoint: 'update_password' }
    ];
    
    forms.forEach(({ id, endpoint }) => {
        const form = document.getElementById(id);
        if (!form) return;
        
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validación especial para contraseñas
            if (id === 'formSeguridad') {
                const passwordNueva = document.getElementById('password_nueva');
                const passwordConfirmar = document.getElementById('password_confirmar');
                
                if (passwordNueva.value !== passwordConfirmar.value) {
                    showToast('Las contraseñas no coinciden', 'error');
                    return;
                }
                
                const strength = calculatePasswordStrength(passwordNueva.value);
                if (strength === 'debil') {
                    showToast('La contraseña es demasiado débil', 'warning');
                    return;
                }
            }
            
            const formData = new FormData(form);
            
            fetch(window.location.pathname, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast(data.message || 'Cambios guardados correctamente', 'success');
                    
                    // Limpiar formulario de contraseña
                    if (id === 'formSeguridad') {
                        form.reset();
                        updatePasswordStrengthUI('debil');
                    }
                } else {
                    showToast(data.message || 'Error al guardar los cambios', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error al procesar la solicitud', 'error');
            });
        });
    });
}

/**
 * Obtiene el token CSRF
 * @returns {string} Token CSRF
 */
function getCsrfToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
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
