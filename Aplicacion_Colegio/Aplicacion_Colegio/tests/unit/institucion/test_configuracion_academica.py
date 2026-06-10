"""
Tests Fase 1: Modelo ConfiguracionAcademica y campo Colegio.tipo.

Verifica:
1. Colegio.tipo acepta los valores del dominio chileno
2. ConfiguracionAcademica se crea correctamente asociada a un Colegio
3. Constraints de unicidad (una config por colegio)
4. Propiedad es_sep
5. Valores por defecto razonables
"""
import pytest
from django.db import IntegrityError

from backend.apps.institucion.models import (
    Colegio,
    ConfiguracionAcademica,
    Region,
    Comuna,
    TipoEstablecimiento,
    DependenciaAdministrativa,
)


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def colegio_base(db):
    region, _ = Region.objects.get_or_create(nombre='Región Test CA')
    comuna, _ = Comuna.objects.get_or_create(
        nombre='Comuna Test CA',
        defaults={'region': region},
    )
    tipo_estab, _ = TipoEstablecimiento.objects.get_or_create(nombre='Tipo Test CA')
    dependencia, _ = DependenciaAdministrativa.objects.get_or_create(nombre='Dep Test CA')
    colegio, _ = Colegio.objects.get_or_create(
        rbd=88881,
        defaults={
            'nombre': 'Colegio Config Test',
            'rut_establecimiento': '88881-K',
            'tipo': 'SUBVENCIONADO',
            'comuna': comuna,
            'tipo_establecimiento': tipo_estab,
            'dependencia': dependencia,
        },
    )
    return colegio


# ---------------------------------------------------------------------------
# 1. Colegio.tipo
# ---------------------------------------------------------------------------

class TestColegioTipo:
    """El campo tipo refleja la dependencia del establecimiento según norma chilena."""

    def test_tipo_por_defecto_es_subvencionado(self, colegio_base):
        assert colegio_base.tipo == 'SUBVENCIONADO'

    @pytest.mark.parametrize('tipo_valido', ['MUNICIPAL', 'SUBVENCIONADO', 'PARTICULAR', 'TP'])
    def test_tipo_acepta_valores_validos(self, colegio_base, tipo_valido):
        colegio_base.tipo = tipo_valido
        colegio_base.save()
        colegio_base.refresh_from_db()
        assert colegio_base.tipo == tipo_valido

    def test_field_choices_contiene_todos_los_tipos(self):
        tipos_esperados = {'MUNICIPAL', 'SUBVENCIONADO', 'PARTICULAR', 'TP'}
        tipos_definidos = {choice[0] for choice in Colegio.TIPO_DEPENDENCIA}
        assert tipos_esperados == tipos_definidos


# ---------------------------------------------------------------------------
# 2. ConfiguracionAcademica — creación y defaults
# ---------------------------------------------------------------------------

class TestConfiguracionAcademica:
    """ConfiguracionAcademica debe poder crearse y tiene valores por defecto sensatos."""

    def test_crear_configuracion_basica(self, colegio_base):
        config = ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
        )
        assert config.pk is not None
        assert config.colegio == colegio_base
        assert config.anio_escolar_activo == 2025

    def test_regimen_evaluacion_default_semestral(self, colegio_base):
        config = ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
        )
        assert config.regimen_evaluacion == 'SEMESTRAL'

    def test_tiene_convenio_sep_default_false(self, colegio_base):
        config = ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
        )
        assert config.tiene_convenio_sep is False

    def test_umbral_inasistencia_default_3(self, colegio_base):
        config = ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
        )
        assert config.umbral_inasistencia_alerta == 3

    def test_umbral_notas_default_4(self, colegio_base):
        config = ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
        )
        assert float(config.umbral_notas_alerta) == 4.0

    def test_propiedad_es_sep_false_cuando_sin_convenio(self, colegio_base):
        config = ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
            tiene_convenio_sep=False,
        )
        assert config.es_sep is False

    def test_propiedad_es_sep_true_cuando_con_convenio(self, colegio_base):
        config = ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
            tiene_convenio_sep=True,
        )
        assert config.es_sep is True

    def test_str_representa_colegio_y_anio(self, colegio_base):
        config = ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
        )
        assert '2025' in str(config)
        assert colegio_base.nombre in str(config)


# ---------------------------------------------------------------------------
# 3. Unicidad: una ConfiguracionAcademica por Colegio
# ---------------------------------------------------------------------------

class TestConfiguracionAcademicaUnicidad:
    """No puede existir más de una ConfiguracionAcademica por colegio (OneToOne)."""

    def test_duplicado_lanza_integrity_error(self, colegio_base):
        ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
        )
        with pytest.raises(IntegrityError):
            ConfiguracionAcademica.objects.create(
                colegio=colegio_base,
                anio_escolar_activo=2026,
            )

    def test_acceso_por_related_name(self, colegio_base):
        config = ConfiguracionAcademica.objects.create(
            colegio=colegio_base,
            anio_escolar_activo=2025,
        )
        assert colegio_base.configuracion_academica == config
