"""
Tests unitarios para auth_helpers
"""
import pytest
from backend.common.utils.auth_helpers import normalizar_rol


class TestNormalizarRol:
    """Tests para la función normalizar_rol"""
    
    def test_normalizar_rol_admin_general(self):
        """Test: Normaliza 'Administrador general' a 'admin_general'"""
        result = normalizar_rol('Administrador general')
        assert result == 'admin_general'
    
    def test_normalizar_rol_admin_escolar(self):
        """Test: Normaliza 'Administrador escolar' a 'admin_escolar'"""
        result = normalizar_rol('Administrador escolar')
        assert result == 'admin_escolar'
    
    def test_normalizar_rol_profesor(self):
        """Test: Normaliza 'Profesor' a 'profesor'"""
        result = normalizar_rol('Profesor')
        assert result == 'profesor'
    
    def test_normalizar_rol_alumno(self):
        """Test: Normaliza 'Alumno' a 'estudiante'"""
        result = normalizar_rol('Alumno')
        assert result == 'estudiante'
    
    def test_normalizar_rol_apoderado(self):
        """Test: Normaliza 'Apoderado' a 'apoderado'"""
        result = normalizar_rol('Apoderado')
        assert result == 'apoderado'
    
    def test_normalizar_rol_asesor_financiero(self):
        """Test: Normaliza 'Asesor financiero' a 'asesor_financiero'"""
        result = normalizar_rol('Asesor financiero')
        assert result == 'asesor_financiero'
    
    def test_normalizar_rol_desconocido(self):
        """Test: Rol desconocido se normaliza a minúsculas"""
        result = normalizar_rol('RolInexistente')
        assert result == 'rolinexistente'
    
    def test_normalizar_rol_vacio(self):
        """Test: String vacío retorna None"""
        result = normalizar_rol('')
        assert result is None
    
    def test_normalizar_rol_case_sensitive(self):
        """Test: La función es case-insensitive"""
        result = normalizar_rol('profesor')  # minúscula
        assert result == 'profesor'
    
    def test_normalizar_rol_con_espacios(self):
        """Test: Rol con espacios extra se normaliza"""
        result = normalizar_rol('Profesor ')  # espacio al final
        assert result == 'profesor'

    def test_normalizar_rol_coordinador_academico(self):
        """Test: Coordinador Académico normaliza a código interno nuevo"""
        result = normalizar_rol('Coordinador Académico')
        assert result == 'coordinador_academico'

    def test_normalizar_rol_inspector_convivencia(self):
        """Test: Inspector normaliza a código interno nuevo"""
        result = normalizar_rol('Inspector')
        assert result == 'inspector_convivencia'

    def test_normalizar_rol_psicologo_orientador(self):
        """Test: Psicólogo Educacional normaliza a código interno nuevo"""
        result = normalizar_rol('Psicólogo educacional')
        assert result == 'psicologo_orientador'

    def test_normalizar_rol_soporte_tecnico_escolar(self):
        """Test: Soporte Técnico Escolar normaliza a código interno nuevo"""
        result = normalizar_rol('Soporte Técnico Escolar')
        assert result == 'soporte_tecnico_escolar'

    def test_normalizar_rol_bibliotecario_digital(self):
        """Test: Bibliotecario normaliza a código interno nuevo"""
        result = normalizar_rol('Bibliotecario')
        assert result == 'bibliotecario_digital'
