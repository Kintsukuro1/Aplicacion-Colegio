from unittest.mock import Mock, patch

from backend.apps.core.services.admin_general_escuelas_query_service import (
    AdminGeneralEscuelasQueryService,
)


@patch('backend.apps.core.services.admin_general_escuelas_query_service.Colegio')
def test_list_escuelas_without_filters_returns_base_queryset(mock_colegio):
    qs = Mock()
    ordered = Mock()
    mock_colegio.objects.select_related.return_value = qs
    qs.order_by.return_value = ordered

    result = AdminGeneralEscuelasQueryService.list_escuelas()

    assert result is ordered


@patch('backend.apps.core.services.admin_general_escuelas_query_service.Colegio')
def test_list_escuelas_with_all_filters_and_search_union(mock_colegio):
    qs = Mock()
    qs_region = Mock()
    qs_tipo = Mock()
    qs_dep = Mock()
    qs_name = Mock()
    qs_rbd = Mock()
    qs_union = Mock()

    mock_colegio.objects.select_related.return_value = qs
    qs.order_by.return_value = qs
    qs.filter.return_value = qs_region
    qs_region.filter.return_value = qs_tipo
    qs_tipo.filter.return_value = qs_dep
    qs_dep.filter.side_effect = [qs_name, qs_rbd]
    qs_name.__or__ = Mock(return_value=qs_union)

    result = AdminGeneralEscuelasQueryService.list_escuelas(
        region_id=1,
        tipo_id=2,
        dependencia_id=3,
        search='escuela',
    )

    assert result is qs_union


@patch('backend.apps.core.services.admin_general_escuelas_query_service.DependenciaAdministrativa')
@patch('backend.apps.core.services.admin_general_escuelas_query_service.TipoEstablecimiento')
@patch('backend.apps.core.services.admin_general_escuelas_query_service.Region')
def test_list_filter_data_branches(mock_region, mock_tipo, mock_dep):
    regiones_with_comunas = Mock()
    regiones_simple = Mock()
    tipos = Mock()
    deps = Mock()
    mock_region.objects.prefetch_related.return_value.all.return_value = regiones_with_comunas
    mock_region.objects.all.return_value = regiones_simple
    mock_tipo.objects.all.return_value = tipos
    mock_dep.objects.all.return_value = deps

    result_true = AdminGeneralEscuelasQueryService.list_filter_data(include_comunas=True)
    result_false = AdminGeneralEscuelasQueryService.list_filter_data(include_comunas=False)

    assert result_true == (regiones_with_comunas, tipos, deps)
    assert result_false == (regiones_simple, tipos, deps)


@patch('backend.apps.core.services.admin_general_escuelas_query_service.Colegio')
def test_get_escuela_helpers(mock_colegio):
    by_rbd = Mock()
    detail = Mock()
    detail_or_none = Mock()
    mock_colegio.objects.get.return_value = by_rbd
    mock_colegio.objects.select_related.return_value.get.return_value = detail
    mock_colegio.objects.select_related.return_value.filter.return_value.first.return_value = detail_or_none

    assert AdminGeneralEscuelasQueryService.get_escuela_by_rbd(123) is by_rbd
    assert AdminGeneralEscuelasQueryService.get_escuela_detail_by_rbd(123) is detail
    assert AdminGeneralEscuelasQueryService.get_escuela_detail_or_none(123) is detail_or_none


@patch('backend.apps.core.services.admin_general_escuelas_query_service.User')
def test_user_counts_and_has_users(mock_user):
    f1 = Mock()
    f2 = Mock()
    f3 = Mock()
    f4 = Mock()
    f1.count.return_value = 10
    f2.count.return_value = 4
    f3.count.return_value = 6
    f4.exists.return_value = True
    mock_user.objects.filter.side_effect = [f1, f2, f3, f4]

    counts = AdminGeneralEscuelasQueryService.get_user_counts_by_school(987)
    has_users = AdminGeneralEscuelasQueryService.has_users_for_school(987)

    assert counts == (10, 4, 6)
    assert has_users is True


@patch('backend.apps.core.services.admin_general_escuelas_query_service.Comuna')
def test_list_comunas_by_region(mock_comuna):
    qs = Mock()
    ordered = Mock()
    mock_comuna.objects.filter.return_value = qs
    qs.order_by.return_value = ordered

    result = AdminGeneralEscuelasQueryService.list_comunas_by_region(5)

    assert result is ordered
