from unittest.mock import Mock, patch

import pytest

from backend.apps.academico.services.tarea_entrega_service import TareaEntregaService


pytestmark = pytest.mark.django_db


@patch('backend.apps.academico.models.EntregaTarea')
def test_upsert_entrega_created_estado_entregada(mock_entrega_tarea):
    tarea = Mock()
    tarea.esta_vencida.return_value = False
    estudiante = Mock()
    archivo = Mock()

    entrega = Mock()
    mock_entrega_tarea.objects.get_or_create.return_value = (entrega, True)

    result, created = TareaEntregaService.upsert_entrega(
        tarea=tarea,
        estudiante=estudiante,
        archivo=archivo,
        comentario='ok',
    )

    assert result is entrega
    assert created is True
    kwargs = mock_entrega_tarea.objects.get_or_create.call_args.kwargs
    assert kwargs['defaults']['estado'] == 'entregada'


@patch('backend.apps.academico.services.tarea_entrega_service.timezone')
@patch('backend.apps.academico.models.EntregaTarea')
def test_upsert_entrega_updates_existing_estado_tarde(mock_entrega_tarea, mock_timezone):
    tarea = Mock()
    tarea.esta_vencida.return_value = True
    estudiante = Mock()
    archivo = Mock()

    entrega = Mock()
    mock_entrega_tarea.objects.get_or_create.return_value = (entrega, False)
    mock_timezone.now.return_value = 'NOW'

    result, created = TareaEntregaService.upsert_entrega(
        tarea=tarea,
        estudiante=estudiante,
        archivo=archivo,
        comentario='comentario',
    )

    assert result is entrega
    assert created is False
    assert entrega.archivo is archivo
    assert entrega.comentario_estudiante == 'comentario'
    assert entrega.fecha_entrega == 'NOW'
    assert entrega.estado == 'tarde'
    entrega.save.assert_called_once()
