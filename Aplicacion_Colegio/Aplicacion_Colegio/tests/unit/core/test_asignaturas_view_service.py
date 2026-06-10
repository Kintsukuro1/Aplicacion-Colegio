from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
import sys

import pytest

from backend.apps.core.services.asignaturas_view_service import AsignaturasViewService


pytestmark = pytest.mark.django_db


class _ReqDict(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def _request(method='GET', get_params=None, post_params=None):
    req = Mock()
    req.method = method
    req.GET = _ReqDict(get_params or {})
    req.POST = _ReqDict(post_params or {})
    req.user = Mock()
    req.user.rbd_colegio = 123
    return req


def _install_core_modules(asignaturas_query, page_obj=None):
    core_mod = ModuleType('core')
    optim_mod = ModuleType('core.optimizations')
    utils_mod = ModuleType('core.utils')
    pag_mod = ModuleType('core.utils.pagination')

    optim_mod.get_asignaturas_optimized = lambda _rbd: asignaturas_query
    pag_mod.PAGINATION_SIZES = {'asignaturas': 10}
    pag_mod.paginate_queryset = lambda _request, _qs, per_page: page_obj if page_obj is not None else _qs

    return patch.dict(
        sys.modules,
        {
            'core': core_mod,
            'core.optimizations': optim_mod,
            'core.utils': utils_mod,
            'core.utils.pagination': pag_mod,
        },
    )


def _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque):
    colegio = Mock()
    colegio.rbd = 123
    mock_colegio.objects.get.return_value = colegio

    curso = Mock()
    curso.id_curso = 10
    curso.nombre = '1A'

    cursos_qs = Mock()
    cursos_qs.select_related.return_value.order_by.return_value = cursos_qs
    cursos_qs.exists.return_value = True
    cursos_qs.first.return_value = curso
    mock_curso.objects.filter.return_value = cursos_qs

    profesores_qs = Mock()
    profesores_qs.order_by.return_value = profesores_qs
    mock_user_model.objects.filter.return_value = profesores_qs

    clase = Mock()
    clase.id = 1
    clase.asignatura = Mock(id_asignatura=7, nombre='Matemática')
    clase.curso = Mock(nombre='1A')
    clase.profesor = Mock()
    clase.profesor.get_full_name.return_value = 'Profesor Uno'

    clases_qs = Mock()
    clases_qs.count.return_value = 4
    clases_qs.select_related.return_value.order_by.return_value = [clase]
    mock_clase.objects.filter.return_value = clases_qs

    bloque_cell = Mock()
    bloque_cell.clase = clase
    bloque_cell.id_bloque = 55
    mock_bloque.objects.filter.return_value.select_related.return_value.first.return_value = bloque_cell

    return colegio


@patch('backend.apps.core.services.asignaturas_view_service.Colegio')
@patch('backend.apps.core.services.asignaturas_view_service.Curso')
@patch('backend.apps.core.services.asignaturas_view_service.User')
@patch('backend.apps.core.services.asignaturas_view_service.Clase')
@patch('backend.apps.cursos.models.BloqueHorario')
def test_handle_get_returns_context(
    mock_bloque,
    mock_clase,
    mock_user_model,
    mock_curso,
    mock_colegio,
):
    req = _request(get_params={'busqueda': 'mat'})

    asignaturas_query = Mock()
    asignaturas_query.filter.return_value = asignaturas_query
    asignaturas_query.count.return_value = 2
    asignaturas_query.aggregate.return_value = {'total': 8}
    asignaturas_query.annotate.return_value.filter.return_value.count.return_value = 1

    _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque)

    with _install_core_modules(asignaturas_query):
        result = AsignaturasViewService.handle(req)

    assert isinstance(result, dict)
    assert result['total_asignaturas'] == 2
    assert result['total_horas_semanales'] == 8
    assert result['asignaturas_sin_asignar'] == 1
    assert result['curso_seleccionado'] is not None
    assert 'clases_por_asignatura_json' in result


@patch('backend.apps.core.services.asignaturas_view_service.Colegio')
@patch('backend.apps.core.services.asignaturas_view_service.Curso')
@patch('backend.apps.core.services.asignaturas_view_service.User')
@patch('backend.apps.core.services.asignaturas_view_service.Clase')
@patch('backend.apps.cursos.models.BloqueHorario')
@patch('backend.apps.core.services.asignaturas_view_service.JsonResponse')
def test_handle_get_json_returns_json_response(
    mock_json_response,
    mock_bloque,
    mock_clase,
    mock_user_model,
    mock_curso,
    mock_colegio,
):
    req = _request(get_params={'json': '1', 'curso_horario': 'abc'})

    asignaturas_query = Mock()
    asignaturas_query.count.return_value = 1
    asignaturas_query.aggregate.return_value = {'total': 4}
    asignaturas_query.annotate.return_value.filter.return_value.count.return_value = 0

    _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque)
    mock_curso.DoesNotExist = Exception

    mock_json_response.return_value = 'JSON_OK'

    with _install_core_modules(asignaturas_query):
        response = AsignaturasViewService.handle(req)

    assert response == 'JSON_OK'
    mock_json_response.assert_called_once()


@patch('backend.apps.core.services.asignaturas_view_service.messages')
@patch('backend.apps.core.services.asignaturas_view_service.AsignaturaHorarioService')
@patch('backend.apps.core.services.asignaturas_view_service.Colegio')
@patch('backend.apps.core.services.asignaturas_view_service.Curso')
@patch('backend.apps.core.services.asignaturas_view_service.User')
@patch('backend.apps.core.services.asignaturas_view_service.Clase')
@patch('backend.apps.cursos.models.BloqueHorario')
def test_post_crear_and_asignar_curso_profesor_success(
    mock_bloque,
    mock_clase,
    mock_user_model,
    mock_curso,
    mock_colegio,
    mock_horario_service,
    mock_messages,
):
    asignaturas_query = Mock()
    asignaturas_query.count.return_value = 1
    asignaturas_query.aggregate.return_value = {'total': 2}
    asignaturas_query.annotate.return_value.filter.return_value.count.return_value = 0

    colegio = _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque)

    with patch('backend.apps.core.services.asignaturas_view_service.ClaseService.create') as mock_clase_create, _install_core_modules(asignaturas_query):
        req_crear = _request(
            method='POST',
            post_params={'accion': 'crear', 'nombre': 'Lenguaje', 'codigo': 'LEN', 'horas_semanales': '5'},
        )
        req_crear.user.rbd_colegio = 123
        AsignaturasViewService.handle(req_crear)

        req_asignar = _request(
            method='POST',
            post_params={'accion': 'asignar_curso_profesor', 'curso_id': '1', 'asignatura_id': '2', 'profesor_id': '3'},
        )
        req_asignar.user.rbd_colegio = 123
        AsignaturasViewService.handle(req_asignar)

    mock_horario_service.create_asignatura.assert_called_once_with(
        school_rbd=colegio.rbd,
        nombre='Lenguaje',
        codigo='LEN',
        horas_semanales=5,
    )
    mock_clase_create.assert_called_once()
    assert mock_messages.success.call_count >= 2


@patch('backend.apps.core.services.asignaturas_view_service.messages')
@patch('backend.apps.core.services.asignaturas_view_service.Asignatura')
@patch('backend.apps.core.services.asignaturas_view_service.Colegio')
@patch('backend.apps.core.services.asignaturas_view_service.Curso')
@patch('backend.apps.core.services.asignaturas_view_service.User')
@patch('backend.apps.core.services.asignaturas_view_service.Clase')
@patch('backend.apps.cursos.models.BloqueHorario')
def test_post_editar_and_eliminar_paths(
    mock_bloque,
    mock_clase,
    mock_user_model,
    mock_curso,
    mock_colegio,
    mock_asignatura,
    mock_messages,
):
    asignaturas_query = Mock()
    asignaturas_query.count.return_value = 2
    asignaturas_query.aggregate.return_value = {'total': 3}
    asignaturas_query.annotate.return_value.filter.return_value.count.return_value = 0

    colegio = _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque)

    asignatura_obj = Mock()
    mock_asignatura.objects.get.return_value = asignatura_obj

    with patch('backend.apps.core.services.asignaturas_view_service.ClaseService.deactivate_by_asignatura') as mock_deactivate, _install_core_modules(asignaturas_query):
        req_editar = _request(
            method='POST',
            post_params={'accion': 'editar', 'id': '5', 'nombre': 'Nueva', 'codigo': 'NV', 'horas_semanales': '6'},
        )
        AsignaturasViewService.handle(req_editar)

        req_eliminar = _request(method='POST', post_params={'accion': 'eliminar', 'id': '5'})
        AsignaturasViewService.handle(req_eliminar)

    assert asignatura_obj.save.call_count == 2
    mock_deactivate.assert_called_once_with(school_rbd=colegio.rbd, asignatura=asignatura_obj)
    assert mock_messages.success.call_count >= 2


@patch('backend.apps.core.services.asignaturas_view_service.redirect')
@patch('backend.apps.core.services.asignaturas_view_service.reverse', return_value='/dashboard/')
@patch('backend.apps.core.services.asignaturas_view_service.messages')
@patch('backend.apps.core.services.asignaturas_view_service.Colegio')
@patch('backend.apps.core.services.asignaturas_view_service.Curso')
@patch('backend.apps.core.services.asignaturas_view_service.User')
@patch('backend.apps.core.services.asignaturas_view_service.Clase')
@patch('backend.apps.cursos.models.BloqueHorario')
def test_post_asignar_bloque_conflicto_profesor_redirects(
    mock_bloque,
    mock_clase,
    mock_user_model,
    mock_curso,
    mock_colegio,
    mock_messages,
    _mock_reverse,
    mock_redirect,
):
    asignaturas_query = Mock()
    asignaturas_query.count.return_value = 1
    asignaturas_query.aggregate.return_value = {'total': 1}
    asignaturas_query.annotate.return_value.filter.return_value.count.return_value = 0

    _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque)

    clase = Mock()
    clase.profesor = Mock()
    clase.profesor.get_full_name.return_value = 'Profesor Uno'
    clase.asignatura = SimpleNamespace(nombre='Historia')
    clase.curso = SimpleNamespace(nombre='1A')
    mock_clase.objects.get.return_value = clase

    filter_qs = Mock()
    filter_qs.exclude.return_value.exists.return_value = True
    mock_bloque.objects.filter.return_value = filter_qs
    mock_redirect.return_value = 'REDIR'

    with _install_core_modules(asignaturas_query):
        req = _request(
            method='POST',
            post_params={
                'accion': 'asignar_bloque',
                'clase_id': '1',
                'dia_semana': '2',
                'bloque_numero': '3',
            },
        )
        result = AsignaturasViewService.handle(req)

    assert result == 'REDIR'
    mock_messages.error.assert_called_once()


@patch('backend.apps.core.services.asignaturas_view_service.messages')
@patch('backend.apps.core.services.asignaturas_view_service.AsignaturaHorarioService')
@patch('backend.apps.core.services.asignaturas_view_service.DisponibilidadProfesor')
@patch('backend.apps.core.services.asignaturas_view_service.Colegio')
@patch('backend.apps.core.services.asignaturas_view_service.Curso')
@patch('backend.apps.core.services.asignaturas_view_service.User')
@patch('backend.apps.core.services.asignaturas_view_service.Clase')
@patch('backend.apps.cursos.models.BloqueHorario')
def test_post_asignar_bloque_success_created_false(
    mock_bloque,
    mock_clase,
    mock_user_model,
    mock_curso,
    mock_colegio,
    mock_disponibilidad,
    mock_horario_service,
    mock_messages,
):
    asignaturas_query = Mock()
    asignaturas_query.count.return_value = 1
    asignaturas_query.aggregate.return_value = {'total': 1}
    asignaturas_query.annotate.return_value.filter.return_value.count.return_value = 0

    _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque)

    clase = Mock()
    clase.profesor = Mock()
    clase.profesor.get_full_name.return_value = 'Profesor Dos'
    clase.asignatura = SimpleNamespace(nombre='Historia')
    clase.curso = SimpleNamespace(nombre='2B')
    mock_clase.objects.get.return_value = clase

    filter_qs = Mock()
    filter_qs.exclude.return_value.exists.side_effect = [False, False]
    filter_qs.select_related.return_value.first.return_value = None
    mock_bloque.objects.filter.return_value = filter_qs

    mock_disponibilidad.objects.filter.return_value.exists.return_value = False
    mock_horario_service.upsert_bloque.return_value = (Mock(), False)

    with _install_core_modules(asignaturas_query):
        req = _request(
            method='POST',
            post_params={
                'accion': 'asignar_bloque',
                'clase_id': '1',
                'dia_semana': '2',
                'bloque_numero': '4',
            },
        )
        AsignaturasViewService.handle(req)

    mock_messages.warning.assert_called()
    mock_messages.success.assert_called()


@patch('backend.apps.core.services.asignaturas_view_service.messages')
@patch('backend.apps.core.services.asignaturas_view_service.Colegio')
@patch('backend.apps.core.services.asignaturas_view_service.Curso')
@patch('backend.apps.core.services.asignaturas_view_service.User')
@patch('backend.apps.core.services.asignaturas_view_service.Clase')
@patch('backend.apps.cursos.models.BloqueHorario')
def test_post_mover_eliminar_cambiar_bloque_and_auto(
    mock_bloque,
    mock_clase,
    mock_user_model,
    mock_curso,
    mock_colegio,
    mock_messages,
):
    asignaturas_query = Mock()
    asignaturas_query.count.return_value = 1
    asignaturas_query.aggregate.return_value = {'total': 1}
    asignaturas_query.annotate.return_value.filter.return_value.count.return_value = 0

    _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque)

    bloque = Mock()
    bloque.id_bloque = 9
    mock_bloque.objects.get.return_value = bloque

    existing_qs = Mock()
    existing_qs.exclude.return_value.first.side_effect = [Mock(), None]
    existing_qs.values_list.return_value = []
    existing_qs.select_related.return_value.first.return_value = None
    mock_bloque.objects.filter.return_value = existing_qs

    clase_nueva = Mock()
    mock_clase.objects.get.return_value = clase_nueva

    clase_auto = Mock()
    clase_auto.asignatura = SimpleNamespace(nombre='Biología', horas_semanales=1)
    clase_auto.curso = SimpleNamespace(nombre='3C')
    clase_auto.profesor = Mock()
    clase_auto.profesor.get_full_name.return_value = 'Profesor Auto'

    auto_qs = MagicMock()
    auto_qs.annotate.return_value.filter.return_value.select_related.return_value = [clase_auto]
    auto_qs.select_related.return_value.order_by.return_value = []
    auto_qs.count.return_value = 0
    mock_clase.objects.filter.return_value = auto_qs

    with patch('backend.apps.core.services.asignaturas_view_service.DisponibilidadProfesor') as mock_disp, patch(
        'backend.apps.core.services.asignaturas_view_service.AsignaturaHorarioService.create_bloque'
    ) as mock_create_bloque, _install_core_modules(asignaturas_query):
        mock_disp.objects.filter.return_value.values_list.return_value = []

        req_elim = _request(method='POST', post_params={'accion': 'eliminar_bloque', 'bloque_id': '9'})
        AsignaturasViewService.handle(req_elim)

        req_mover_conf = _request(
            method='POST',
            post_params={'accion': 'mover_bloque', 'bloque_id': '9', 'nuevo_dia': '1', 'nuevo_bloque': '2'},
        )
        AsignaturasViewService.handle(req_mover_conf)

        req_mover_ok = _request(
            method='POST',
            post_params={'accion': 'mover_bloque', 'bloque_id': '9', 'nuevo_dia': '3', 'nuevo_bloque': '4'},
        )
        AsignaturasViewService.handle(req_mover_ok)

        req_cambiar = _request(
            method='POST',
            post_params={'accion': 'cambiar_curso_bloque', 'bloque_id': '9', 'nueva_clase_id': '77'},
        )
        AsignaturasViewService.handle(req_cambiar)

        req_auto = _request(method='POST', post_params={'accion': 'asignar_automatico'})
        AsignaturasViewService.handle(req_auto)

    assert bloque.save.call_count >= 3
    mock_create_bloque.assert_not_called()
    mock_messages.error.assert_called()
    mock_messages.warning.assert_called()
    mock_messages.info.assert_called()


@patch('backend.apps.core.services.asignaturas_view_service.messages')
@patch('backend.apps.core.services.asignaturas_view_service.AsignaturaHorarioService')
@patch('backend.apps.core.services.asignaturas_view_service.Asignatura')
@patch('backend.apps.core.services.asignaturas_view_service.Colegio')
@patch('backend.apps.core.services.asignaturas_view_service.Curso')
@patch('backend.apps.core.services.asignaturas_view_service.User')
@patch('backend.apps.core.services.asignaturas_view_service.Clase')
@patch('backend.apps.cursos.models.BloqueHorario')
def test_post_error_paths_cover_exceptions(
    mock_bloque,
    mock_clase,
    mock_user_model,
    mock_curso,
    mock_colegio,
    mock_asignatura,
    mock_horario_service,
    mock_messages,
):
    asignaturas_query = Mock()
    asignaturas_query.count.return_value = 1
    asignaturas_query.aggregate.return_value = {'total': 1}
    asignaturas_query.annotate.return_value.filter.return_value.count.return_value = 0

    _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque)

    with patch('backend.apps.core.services.asignaturas_view_service.ClaseService.create', side_effect=Exception('x')), patch(
        'backend.apps.core.services.asignaturas_view_service.ClaseService.deactivate_by_asignatura', side_effect=Exception('x')
    ), patch('backend.apps.core.services.asignaturas_view_service.AsignaturaHorarioService.upsert_bloque', side_effect=Exception('x')), patch(
        'backend.apps.core.services.asignaturas_view_service.DisponibilidadProfesor'
    ) as mock_disp, _install_core_modules(asignaturas_query):
        mock_horario_service.create_asignatura.side_effect = Exception('x')
        mock_asignatura.objects.get.side_effect = Exception('x')
        mock_bloque.objects.get.side_effect = Exception('x')
        mock_clase.objects.get.side_effect = Exception('x')
        mock_disp.objects.filter.return_value.exists.return_value = True

        actions = [
            {'accion': 'crear', 'horas_semanales': '3'},
            {'accion': 'editar', 'id': '1', 'horas_semanales': '3'},
            {'accion': 'eliminar', 'id': '1'},
            {'accion': 'asignar_curso_profesor', 'curso_id': '1', 'asignatura_id': '2', 'profesor_id': '3'},
            {'accion': 'asignar_bloque', 'clase_id': '1', 'dia_semana': '1', 'bloque_numero': '1'},
            {'accion': 'eliminar_bloque', 'bloque_id': '1'},
            {'accion': 'mover_bloque', 'bloque_id': '1', 'nuevo_dia': '1', 'nuevo_bloque': '2'},
            {'accion': 'cambiar_curso_bloque', 'bloque_id': '1', 'nueva_clase_id': '2'},
        ]

        for payload in actions:
            req = _request(method='POST', post_params=payload)
            AsignaturasViewService.handle(req)

    assert mock_messages.error.call_count >= 8


@patch('backend.apps.core.services.asignaturas_view_service.messages')
@patch('backend.apps.core.services.asignaturas_view_service.Colegio')
@patch('backend.apps.core.services.asignaturas_view_service.Curso')
@patch('backend.apps.core.services.asignaturas_view_service.User')
@patch('backend.apps.core.services.asignaturas_view_service.Clase')
@patch('backend.apps.cursos.models.BloqueHorario')
def test_post_asignar_automatico_assigns_blocks(
    mock_bloque,
    mock_clase,
    mock_user_model,
    mock_curso,
    mock_colegio,
    mock_messages,
):
    asignaturas_query = Mock()
    asignaturas_query.count.return_value = 1
    asignaturas_query.aggregate.return_value = {'total': 1}
    asignaturas_query.annotate.return_value.filter.return_value.count.return_value = 0

    _setup_common_query_mocks(mock_colegio, mock_curso, mock_user_model, mock_clase, mock_bloque)

    clase_auto = Mock()
    clase_auto.asignatura = SimpleNamespace(nombre='Física', horas_semanales=1)
    clase_auto.curso = SimpleNamespace(nombre='2A')
    clase_auto.profesor = Mock()
    clase_auto.profesor.get_full_name.return_value = 'Prof Física'

    post_filter_qs = MagicMock()
    post_filter_qs.annotate.return_value.filter.return_value.select_related.return_value = [clase_auto]
    post_filter_qs.select_related.return_value.order_by.return_value = []
    post_filter_qs.count.return_value = 0
    mock_clase.objects.filter.return_value = post_filter_qs

    block_qs = Mock()
    block_qs.values_list.return_value = []
    block_qs.select_related.return_value.first.return_value = None
    mock_bloque.objects.filter.return_value = block_qs

    with patch('backend.apps.core.services.asignaturas_view_service.DisponibilidadProfesor') as mock_disp, patch(
        'backend.apps.core.services.asignaturas_view_service.AsignaturaHorarioService.create_bloque'
    ) as mock_create_bloque, _install_core_modules(asignaturas_query):
        mock_disp.objects.filter.return_value.values_list.return_value = [(1, 1)]

        req = _request(method='POST', post_params={'accion': 'asignar_automatico'})
        AsignaturasViewService.handle(req)

    mock_create_bloque.assert_called()
    mock_messages.success.assert_called()
