/** INICIO - ESTUDIANTE */

document.addEventListener('DOMContentLoaded', function() {
    initCardsAnimation();
    showWelcomeMessage();
});

// Animación de entrada para las cards
function initCardsAnimation() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.3s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 30);
    });
}

// Mostrar mensaje de bienvenida
function showWelcomeMessage() {
    setTimeout(() => {
        if (typeof ToastManager !== 'undefined') {
            ToastManager.info('¡Bienvenido a tu portal estudiantil! 🎓', 4000);
        }
    }, 500);
}
