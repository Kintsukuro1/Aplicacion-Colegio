/**
 * Gestión de asignaturas — Admin Escolar
 * Modales (.active), acciones de tabla y horario semanal.
 */
(function () {
    'use strict';

    var clasesData = {};
    var draggedElement = null;
    var selectorActivo = null;

    function abrirModal(modalId) {
        var modal = document.getElementById(modalId);
        if (!modal) return;
        modal.classList.add('active');
        document.body.classList.add('asig-modal-open');
    }

    function cerrarModal(modalId) {
        var modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('active');
        if (!document.querySelector('.modal-overlay.active')) {
            document.body.classList.remove('asig-modal-open');
        }
    }

    function abrirModalCrear() {
        document.getElementById('modalTitulo').textContent = 'Nueva Asignatura';
        document.getElementById('accionForm').value = 'crear';
        document.getElementById('asignaturaId').value = '';
        document.getElementById('nombre').value = '';
        document.getElementById('codigo').value = '';
        document.getElementById('horas_semanales').value = '0';
        abrirModal('modalAsignatura');
    }

    function abrirModalEditar(button) {
        var data = button.dataset;
        document.getElementById('modalTitulo').textContent = 'Editar Asignatura';
        document.getElementById('accionForm').value = 'editar';
        document.getElementById('asignaturaId').value = data.id || '';
        document.getElementById('nombre').value = data.nombre || '';
        document.getElementById('codigo').value = data.codigo || '';
        document.getElementById('horas_semanales').value = data.horas || '0';
        abrirModal('modalAsignatura');
    }

    function abrirModalAsignar(button) {
        var data = button.dataset;
        document.getElementById('asignarAsignaturaId').value = data.id || '';
        document.getElementById('asignarAsignaturaNombre').textContent = data.nombre || '';
        document.getElementById('curso_id').value = '';
        document.getElementById('profesor_id').value = '';
        abrirModal('modalAsignar');
    }

    function confirmarEliminar(button) {
        var data = button.dataset;
        var nombre = data.nombre || 'esta asignatura';
        if (window.confirm('¿Está seguro que desea desactivar la asignatura "' + nombre + '"?\n\nLas clases asociadas también serán desactivadas.')) {
            document.getElementById('eliminarId').value = data.id || '';
            document.getElementById('formEliminar').submit();
        }
    }

    function abrirModalAsignarBloque() {
        abrirModal('modalAsignarBloque');
    }

    function abrirModalAsignarBloqueRapido(dia, bloque) {
        document.getElementById('dia_semana').value = dia;
        document.getElementById('bloque_numero').value = bloque;
        abrirModal('modalAsignarBloque');
    }

    function onAccionClick(event) {
        var btn = event.target.closest('[data-asig-action]');
        if (!btn) return;
        event.preventDefault();
        event.stopPropagation();
        var action = btn.getAttribute('data-asig-action');
        if (action === 'crear') abrirModalCrear();
        else if (action === 'editar') abrirModalEditar(btn);
        else if (action === 'asignar') abrirModalAsignar(btn);
        else if (action === 'eliminar') confirmarEliminar(btn);
    }

    function bindModales() {
        document.querySelectorAll('.modal-overlay').forEach(function (modal) {
            modal.addEventListener('click', function (e) {
                if (e.target === modal) cerrarModal(modal.id);
            });
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal-overlay.active').forEach(function (modal) {
                    modal.classList.remove('active');
                });
                document.body.classList.remove('asig-modal-open');
            }
        });
    }

    function loadClasesData() {
        var node = document.getElementById('clases-data');
        if (!node) return;
        try {
            clasesData = JSON.parse(node.textContent || '{}');
        } catch (err) {
            clasesData = {};
            console.warn('No se pudo cargar clases-data', err);
        }
    }

    function bindFiltroBusqueda() {
        var form = document.getElementById('filtrosAsignaturasForm');
        var input = document.getElementById('busqueda');
        if (!form || !input) return;
        var timer = null;
        input.addEventListener('input', function () {
            clearTimeout(timer);
            timer = setTimeout(function () { form.submit(); }, 450);
        });
    }

    function bindAbrirModalQuery() {
        var params = new URLSearchParams(window.location.search);
        if (params.get('abrir_modal') === 'crear') {
            setTimeout(abrirModalCrear, 120);
        }
    }

    // Horario — drag & drop
    window.drag = function (event) {
        draggedElement = event.target.closest('.bloque-clase') || event.target;
        if (draggedElement) draggedElement.classList.add('dragging');
        event.dataTransfer.effectAllowed = 'move';
    };

    window.allowDrop = function (event) {
        event.preventDefault();
        event.currentTarget.classList.add('drag-over');
    };

    window.dragLeave = function (event) {
        event.currentTarget.classList.remove('drag-over');
    };

    window.drop = function (event) {
        event.preventDefault();
        event.currentTarget.classList.remove('drag-over');
        if (!draggedElement) return;
        var celda = event.currentTarget;
        document.getElementById('moverBloqueId').value = draggedElement.dataset.bloqueId || '';
        document.getElementById('moverNuevoDia').value = celda.dataset.dia || '';
        document.getElementById('moverNuevoBloque').value = celda.dataset.bloque || '';
        document.getElementById('formMoverBloque').submit();
        draggedElement.classList.remove('dragging');
        draggedElement = null;
    };

    window.eliminarBloque = function (bloqueId) {
        if (window.confirm('¿Está seguro que desea eliminar este bloque del horario?')) {
            document.getElementById('eliminarBloqueId').value = bloqueId;
            document.getElementById('formEliminarBloque').submit();
        }
    };

    window.abrirSelectorCurso = function (event, bloqueId, asignaturaId) {
        event.stopPropagation();
        event.preventDefault();
        var selector = document.getElementById('selectorCurso');
        var listaCursos = document.getElementById('listaCursos');
        if (!selector || !listaCursos) return;
        listaCursos.innerHTML = '';
        var clasesFiltradas = clasesData[String(asignaturaId)] || [];
        if (!clasesFiltradas.length) {
            listaCursos.innerHTML = '<p style="color:#9ca3af;padding:10px;">No hay otros cursos disponibles para esta asignatura.</p>';
        } else {
            clasesFiltradas.forEach(function (clase) {
                var option = document.createElement('div');
                option.className = 'curso-option';
                option.innerHTML = '<div class="curso-option-nombre">' + clase.curso_nombre + '</div>' +
                    '<div class="curso-option-profesor">' + clase.profesor_nombre + '</div>';
                option.onclick = function () { cambiarCurso(bloqueId, clase.clase_id); };
                listaCursos.appendChild(option);
            });
        }
        var rect = event.target.getBoundingClientRect();
        selector.style.display = 'block';
        selector.style.left = (rect.left - 250) + 'px';
        selector.style.top = (rect.top + 25) + 'px';
        selectorActivo = bloqueId;
    };

    window.cerrarSelectorCurso = function () {
        var selector = document.getElementById('selectorCurso');
        if (selector) selector.style.display = 'none';
        selectorActivo = null;
    };

    window.cambiarCurso = function (bloqueId, nuevaClaseId) {
        document.getElementById('cambiarCursoBloqueId').value = bloqueId;
        document.getElementById('cambiarCursoNuevaClaseId').value = nuevaClaseId;
        document.getElementById('formCambiarCurso').submit();
    };

    window.verificarConflicto = function () {
        var claseSelect = document.getElementById('clase_bloque');
        var diaSelect = document.getElementById('dia_semana');
        var bloqueSelect = document.getElementById('bloque_numero');
        var alerta = document.getElementById('alerta-conflicto');
        if (!alerta || !claseSelect || !diaSelect || !bloqueSelect) return;
        if (!claseSelect.value || !diaSelect.value || !bloqueSelect.value) {
            alerta.classList.add('d-none');
            alerta.classList.remove('is-visible');
            return;
        }
        var dia = diaSelect.value;
        var bloque = bloqueSelect.value;
        var celda = document.querySelector('td[data-dia="' + dia + '"][data-bloque="' + bloque + '"]');
        if (celda && celda.querySelector('.bloque-clase')) {
            var bloqueExistente = celda.querySelector('.bloque-clase');
            document.getElementById('mensaje-conflicto').textContent =
                'Ya existe ' + bloqueExistente.querySelector('.asignatura-nombre').textContent +
                ' (' + bloqueExistente.querySelector('.curso-nombre').textContent + ') en este horario.';
            alerta.classList.remove('d-none');
            alerta.classList.add('is-visible');
            return;
        }
        var option = claseSelect.options[claseSelect.selectedIndex];
        var asignaturaNombre = option && option.dataset ? option.dataset.asignatura : '';
        var celdas = document.querySelectorAll('td[data-dia="' + dia + '"][data-bloque="' + bloque + '"] .bloque-clase');
        for (var i = 0; i < celdas.length; i++) {
            var bloqueEl = celdas[i];
            if (bloqueEl.querySelector('.asignatura-nombre').textContent === asignaturaNombre) {
                document.getElementById('mensaje-conflicto').textContent =
                    'La asignatura ' + asignaturaNombre + ' ya está programada en ' +
                    bloqueEl.querySelector('.curso-nombre').textContent + ' a esta hora.';
                alerta.classList.remove('d-none');
                alerta.classList.add('is-visible');
                return;
            }
        }
        alerta.classList.add('d-none');
        alerta.classList.remove('is-visible');
    };

    window.validarAsignacionBloque = function () {
        var alertaConflicto = document.getElementById('alerta-conflicto');
        if (alertaConflicto && alertaConflicto.classList.contains('is-visible')) {
            return window.confirm('Hay un conflicto detectado. ¿Desea continuar de todas formas?');
        }
        return true;
    };

    window.asignarAutomatico = function () {
        if (!window.confirm('¿Desea asignar automáticamente todas las clases sin horario?')) return;
        var root = document.getElementById('asigPageRoot');
        var postUrl = root ? root.getAttribute('data-post-url') : '';
        if (!postUrl) return;
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = postUrl;
        var csrf = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrf) {
            var csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrf.value;
            form.appendChild(csrfInput);
        }
        var accionInput = document.createElement('input');
        accionInput.type = 'hidden';
        accionInput.name = 'accion';
        accionInput.value = 'asignar_automatico';
        form.appendChild(accionInput);
        document.body.appendChild(form);
        form.submit();
    };

    window.cambiarCursoHorario = function () {
        var selector = document.getElementById('selectorCursoHorario');
        if (!selector) return;
        var url = new URL(window.location.href);
        url.searchParams.set('pagina', 'gestionar_asignaturas');
        url.searchParams.set('curso_horario', selector.value);
        sessionStorage.setItem('scrollPos', String(window.scrollY));
        window.location.href = url.toString();
    };

    function initPage() {
        loadClasesData();
        bindModales();
        bindFiltroBusqueda();
        bindAbrirModalQuery();
        document.addEventListener('click', onAccionClick);

        document.addEventListener('click', function (e) {
            var selector = document.getElementById('selectorCurso');
            if (selector && !selector.contains(e.target) && !e.target.classList.contains('btn-cambiar-curso')) {
                cerrarSelectorCurso();
            }
        });

        var scrollPos = sessionStorage.getItem('scrollPos');
        if (scrollPos) {
            window.scrollTo(0, parseInt(scrollPos, 10));
            sessionStorage.removeItem('scrollPos');
        }
    }

    window.cerrarModal = cerrarModal;
    window.abrirModalCrear = abrirModalCrear;
    window.abrirModalEditar = abrirModalEditar;
    window.abrirModalAsignar = abrirModalAsignar;
    window.confirmarEliminar = confirmarEliminar;
    window.abrirModalAsignarBloque = abrirModalAsignarBloque;
    window.abrirModalAsignarBloqueRapido = abrirModalAsignarBloqueRapido;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPage);
    } else {
        initPage();
    }
})();
