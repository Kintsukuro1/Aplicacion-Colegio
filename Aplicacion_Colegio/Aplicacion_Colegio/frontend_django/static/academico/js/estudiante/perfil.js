/** PERFIL - ESTUDIANTE */

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initPasswordValidation();
    initCardsAnimation();
});

// Cambiar foto de perfil
function cambiarFoto(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        
        // Validation: only images allowed
        if (!file.type.startsWith('image/')) {
            if (typeof ToastManager !== 'undefined') {
                ToastManager.error('El archivo debe ser una imagen válida (PNG, JPG, JPEG).');
            } else {
                alert('El archivo debe ser una imagen válida (PNG, JPG, JPEG).');
            }
            return;
        }

        // Simular progreso de subida por AJAX
        if (typeof ToastManager !== 'undefined') {
            ToastManager.info('Iniciando subida de la imagen...', 1500);
        }

        const avatarImg = document.querySelector('.profile-avatar') || document.querySelector('.avatar-preview img') || document.querySelector('.avatar-initials');
        if (avatarImg) {
            avatarImg.style.opacity = '0.5';
            avatarImg.style.filter = 'blur(2px)';
            avatarImg.style.transition = 'all 0.3s ease';
        }

        // Crear una barra de carga simulada o indicador
        setTimeout(() => {
            if (typeof ToastManager !== 'undefined') {
                ToastManager.info('Subiendo: 50% completado...', 1000);
            }
        }, 1000);

        setTimeout(() => {
            if (typeof ToastManager !== 'undefined') {
                ToastManager.success('¡Foto de perfil actualizada exitosamente!');
            } else {
                alert('¡Foto de perfil actualizada exitosamente!');
            }

            // Previsualizar e insertar imagen de forma premium en el DOM
            const reader = new FileReader();
            reader.onload = function(e) {
                if (avatarImg) {
                    avatarImg.style.opacity = '1';
                    avatarImg.style.filter = 'none';
                    if (avatarImg.tagName === 'IMG') {
                        avatarImg.src = e.target.result;
                    } else {
                        // Si era un div con iniciales, lo reemplazamos o inyectamos una etiqueta img
                        const parent = avatarImg.parentElement;
                        if (parent) {
                            parent.innerHTML = `<img src="${e.target.result}" class="profile-avatar img-fluid rounded-circle" style="width: 120px; height: 120px; object-fit: cover; border: 4px solid #fff; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);">`;
                        }
                    }
                }
            };
            reader.readAsDataURL(file);
        }, 2500);
    }
}

// Validar que las contraseñas coincidan
function initPasswordValidation() {
    const passwordConfirm = document.getElementById('password_confirmar');
    
    if (passwordConfirm) {
        passwordConfirm.addEventListener('input', function() {
            const nueva = document.getElementById('password_nueva').value;
            const confirmar = this.value;
            
            if (nueva && confirmar && nueva !== confirmar) {
                this.setCustomValidity('Las contraseñas no coinciden');
            } else {
                this.setCustomValidity('');
            }
        });
    }
}

// Resetear formulario de seguridad
function resetSecurityForm() {
    const form = document.querySelector('#seguridad form');
    if (form) {
        form.reset();
    }
}

// Inicializar tabs
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const panes = document.querySelectorAll('.tab-pane');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetId = this.getAttribute('data-tab');
            
            // Actualizar tabs activos
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Actualizar panes activos
            panes.forEach(pane => {
                if (pane.id === targetId) {
                    pane.classList.add('active');
                } else {
                    pane.classList.remove('active');
                }
            });
        });
    });
}

// Animación de entrada
function initCardsAnimation() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.3s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 80);
    });
}
