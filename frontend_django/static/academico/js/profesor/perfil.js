/** PERFIL - PROFESOR */

document.addEventListener('DOMContentLoaded', function() {
    initTabs();
    initPasswordValidation();
    initCardsAnimation();
});

function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const panes = document.querySelectorAll('.tab-pane');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetId = this.getAttribute('data-tab');
            
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
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

function resetSecurityForm() {
    const form = document.querySelector('#seguridad form');
    if (form) {
        form.reset();
    }
}

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
