/** INICIO - PROFESOR */

document.addEventListener('DOMContentLoaded', function() {
    initCardsAnimation();
    showWelcomeMessage();
});

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

function showWelcomeMessage() {
    setTimeout(() => {
        if (typeof ToastManager !== 'undefined') {
            ToastManager.info('¡Bienvenido al portal docente! 👨‍🏫', 4000);
        }
    }, 500);
}
