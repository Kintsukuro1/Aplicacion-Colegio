"""
Tests Fase 1: Rol Jefe UTP — capabilities y normalización de rol.

Verifica:
1. 'jefe_utp' tiene sus propias capabilities (no comparte las de coordinador_academico)
2. Las nuevas capabilities Chile existen en CAPABILITIES
3. normalizar_rol() mapea correctamente los alias del Jefe UTP
4. PolicyService otorga/niega capabilities según corresponde
"""
import pytest
from backend.common.capabilities import CAPABILITIES, DEFAULT_CAPABILITIES_BY_ROLE
from backend.common.utils.auth_helpers import normalizar_rol, obtener_nombre_rol_display


# ---------------------------------------------------------------------------
# 1. Catálogo de capabilities
# ---------------------------------------------------------------------------

class TestNuevasCapabilitiesChile:
    """Las capabilities del plan Chile deben estar declaradas en CAPABILITIES."""

    CAPS_ESPERADAS = [
        'ACADEMIC_SUPERVISION',
        'LIBRO_CLASE_FIRMAR',
        'LIBRO_CLASE_VIEW_RBD',
        'SEP_VIEW',
        'SEP_MANAGE',
        'SEP_REPORT_EXPORT',
        'ALERT_VIEW',
        'ALERT_MANAGE',
        'ALERT_RESOLVE',
        'CERTIFICATE_EMIT',
    ]

    def test_todas_las_capabilities_chile_estan_en_catalogo(self):
        for cap in self.CAPS_ESPERADAS:
            assert cap in CAPABILITIES, f"Capability '{cap}' falta en CAPABILITIES"

    def test_no_hay_duplicados_en_catalogo(self):
        assert len(CAPABILITIES) == len(set(CAPABILITIES)), \
            "Existen capabilities duplicadas en el catálogo"


# ---------------------------------------------------------------------------
# 2. Rol jefe_utp en DEFAULT_CAPABILITIES_BY_ROLE
# ---------------------------------------------------------------------------

class TestJefeUtpCapabilities:
    """jefe_utp debe tener su propio bloque de capabilities."""

    def test_jefe_utp_existe_en_default_capabilities_by_role(self):
        assert 'jefe_utp' in DEFAULT_CAPABILITIES_BY_ROLE, \
            "'jefe_utp' no está en DEFAULT_CAPABILITIES_BY_ROLE"

    def test_jefe_utp_tiene_academic_supervision(self):
        assert 'ACADEMIC_SUPERVISION' in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']

    def test_jefe_utp_tiene_libro_clase_firmar(self):
        assert 'LIBRO_CLASE_FIRMAR' in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']

    def test_jefe_utp_tiene_libro_clase_view_rbd(self):
        assert 'LIBRO_CLASE_VIEW_RBD' in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']

    def test_jefe_utp_tiene_sep_view(self):
        assert 'SEP_VIEW' in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']

    def test_jefe_utp_tiene_sep_report_export(self):
        assert 'SEP_REPORT_EXPORT' in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']

    def test_jefe_utp_tiene_alert_view(self):
        assert 'ALERT_VIEW' in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']

    def test_jefe_utp_tiene_certificate_emit(self):
        assert 'CERTIFICATE_EMIT' in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']

    def test_jefe_utp_tiene_planning_approve(self):
        assert 'PLANNING_APPROVE' in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']

    def test_jefe_utp_no_tiene_sep_manage_por_defecto(self):
        """SEP_MANAGE es una capability más sensible no asignada por defecto al UTP."""
        # jefe_utp tiene visibilidad SEP pero la gestión directa queda para admin_escolar
        assert 'SEP_MANAGE' not in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']

    def test_todas_las_caps_jefe_utp_estan_en_catalogo(self):
        for cap in DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']:
            assert cap in CAPABILITIES, \
                f"jefe_utp tiene capability '{cap}' que no existe en el catálogo"

    def test_jefe_utp_distinto_a_coordinador_academico(self):
        """jefe_utp debe ser un rol diferente a coordinador_academico."""
        caps_utp = DEFAULT_CAPABILITIES_BY_ROLE['jefe_utp']
        caps_coord = DEFAULT_CAPABILITIES_BY_ROLE['coordinador_academico']
        # jefe_utp tiene capabilities que coordinador no tiene
        extras = caps_utp - caps_coord
        assert len(extras) > 0, \
            "jefe_utp no tiene capabilities adicionales respecto a coordinador_academico"


# ---------------------------------------------------------------------------
# 3. Normalización de rol
# ---------------------------------------------------------------------------

class TestNormalizarRolJefeUtp:
    """normalizar_rol() debe mapear los alias del Jefe UTP a 'jefe_utp'."""

    @pytest.mark.parametrize('alias', [
        'jefe utp',
        'jefe_utp',
        'utp',
        'UTP',
        'Jefe UTP',
        'JEFE UTP',
    ])
    def test_alias_mapea_a_jefe_utp(self, alias):
        resultado = normalizar_rol(alias)
        assert resultado == 'jefe_utp', \
            f"normalizar_rol('{alias}') retornó '{resultado}', esperado 'jefe_utp'"

    def test_coordinador_academico_sigue_mapeando_correctamente(self):
        """Los alias del coordinador no deben interferir con jefe_utp."""
        assert normalizar_rol('coordinador_academico') == 'coordinador_academico'
        assert normalizar_rol('coordinador académico') == 'coordinador_academico'

    def test_jefe_utp_ya_no_mapea_a_coordinador_academico(self):
        """jefe_utp es ahora un rol autónomo — no se fusiona con coordinador."""
        resultado = normalizar_rol('jefe_utp')
        assert resultado != 'coordinador_academico', \
            "jefe_utp no debe mapearse a coordinador_academico"


class TestDisplayNamesRolesSeparados:
    """Display names deben reflejar coordinador y jefe UTP como roles distintos."""

    def test_display_name_coordinador_academico(self):
        assert obtener_nombre_rol_display('coordinador_academico') == 'Coordinador Académico'

    def test_display_name_jefe_utp(self):
        assert obtener_nombre_rol_display('jefe_utp') == 'Jefe UTP'
