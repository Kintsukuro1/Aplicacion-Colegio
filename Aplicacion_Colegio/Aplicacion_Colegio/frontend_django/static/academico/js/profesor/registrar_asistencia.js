/** REGISTRAR ASISTENCIA - PROFESOR */

// Marcar todos con un estado
function marcarTodos(estado) {
    const radios = document.querySelectorAll(`input[type="radio"][value="${estado}"]`);
    radios.forEach(radio => {
        radio.checked = true;
    });
    
    if (typeof ToastManager !== 'undefined') {
        const texto = estado === 'P' ? 'presentes' : estado === 'A' ? 'ausentes' : 'con tardanza';
        ToastManager.success(`Todos marcados como ${texto}`);
    }
}

// Confirmar antes de enviar
document.getElementById('formAsistencia')?.addEventListener('submit', function(e) {
    const checked = document.querySelectorAll('input[type="radio"]:checked').length;
    if (checked === 0) {
        e.preventDefault();
        alert('Debes marcar al menos un estudiante');
        return false;
    }
});
