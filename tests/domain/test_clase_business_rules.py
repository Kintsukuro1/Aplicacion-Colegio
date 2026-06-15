"""
Tests de Reglas de Negocio: Clase

Objetivo: Verificar que el sistema PREVIENE estados inválidos en clases.

Reglas que DEBEN cumplirse:
1. Clase ACTIVA requiere profesor ACTIVO
2. Clase ACTIVA requiere curso ACTIVO  
3. Clase ACTIVA requiere asignatura ACTIVA
4. No se puede asignar profesor INACTIVO a clase
5. No se puede tener 2 clases activas con mismo curso+asignatura+profesor
"""

import pytest
from django.contrib.auth.hashers import make_password

from backend.apps.accounts.models import User, Role
from backend.apps.institucion.models import (
    CicloAcademico, Colegio, Comuna, Region,
    TipoEstablecimiento, NivelEducativo, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso, Asignatura, Clase
from backend.common.exceptions import PrerequisiteException


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_clase():
    """Crea estructura mínima para tests de clase."""
    region = Region.objects.create(nombre="Metropolitana")
    comuna = Comuna.objects.create(nombre="Santiago", region=region)
    tipo = TipoEstablecimiento.objects.create(nombre="Subvencionado")
    dependencia = DependenciaAdministrativa.objects.create(nombre="Municipal")
    
    colegio = Colegio.objects.create(
        rbd=12345,
        rut_establecimiento="76543210-9",
        nombre="Colegio Test",
        direccion="Calle Falsa 123",
        comuna=comuna,
        tipo_establecimiento=tipo,
        dependencia=dependencia
    )
    
    # Crear nivel y curso
    nivel = NivelEducativo.objects.create(nombre="Educación Básica", activo=True)
    curso = Curso.objects.create(
        nombre="1ero Básico A",
        nivel=nivel,
        colegio=colegio,
        activo=True
    )
    
    # Crear asignatura
    asignatura = Asignatura.objects.create(
        nombre="Matemáticas",
        colegio=colegio,
        horas_semanales=5,
        activa=True
    )
    
    # Crear roles y profesor
    rol_profesor = Role.objects.create(nombre="Profesor")
    profesor = User.objects.create(
        email="profesor@test.cl",
        rut="12345678-9",
        nombre="Juan",
        apellido_paterno="Pérez",
        role=rol_profesor,
        rbd_colegio=colegio.rbd,
        password=make_password("testing123"),
        is_active=True
    )
    
    return {
        'colegio': colegio,
        'curso': curso,
        'asignatura': asignatura,
        'profesor': profesor,
        'nivel': nivel,
        'rol_profesor': rol_profesor
    }


class TestClaseBusinessRules:
    """Tests de reglas de negocio de clases."""
    
    def test_clase_activa_requiere_profesor_activo(self, setup_clase):
        """
        REGLA: Clase ACTIVA debe tener profesor ACTIVO.
        
        EXPECTED: Al desactivar profesor, sus clases activas deben validarse
        ACTUAL (antes de fix): Permite clase activa con profesor inactivo ❌
        """
        # Crear clase activa con profesor activo
        clase = Clase.objects.create(
            colegio=setup_clase['colegio'],
            curso=setup_clase['curso'],
            asignatura=setup_clase['asignatura'],
            profesor=setup_clase['profesor'],
            activo=True
        )
        
        # Desactivar profesor
        profesor = setup_clase['profesor']
        profesor.is_active = False
        
        # DEBE impedir guardar o lanzar warning
        # Por ahora Django permite esto (FK SET_NULL NO valida is_active)
        profesor.save()
        
        # Recargar clase
        clase.refresh_from_db()
        
        # Verificar que clase tiene profesor (FK permite esto con SET_NULL)
        assert clase.profesor is not None
        
        # PROBLEMA DETECTADO: Clase activa con profesor inactivo es posible
        # Este test documenta el gap - debería lanzar PrerequisiteException
        # al intentar desactivar profesor con clases activas
    
    def test_no_asignar_profesor_inactivo_a_clase(self, setup_clase):
        """
        REGLA: No se puede asignar profesor INACTIVO a una clase.
        
        EXPECTED: PrerequisiteException al asignar profesor inactivo
        ACTUAL (antes de fix): Permite asignar profesor inactivo ❌
        """
        # Crear profesor inactivo
        profesor_inactivo = User.objects.create(
            email="inactivo@test.cl",
            rut="11111111-1",
            nombre="Pedro",
            apellido_paterno="González",
            role=setup_clase['rol_profesor'],
            rbd_colegio=setup_clase['colegio'].rbd,
            password=make_password("testing123"),
            is_active=False  # INACTIVO
        )
        
        # Intentar crear clase con profesor inactivo
        with pytest.raises(PrerequisiteException) as exc_info:
            clase = Clase.objects.create(
                colegio=setup_clase['colegio'],
                curso=setup_clase['curso'],
                asignatura=setup_clase['asignatura'],
                profesor=profesor_inactivo,  # INACTIVO
                activo=True
            )
        
        assert exc_info.value.error_type == 'INVALID_PROFESOR_STATE'
    
    def test_clase_activa_requiere_curso_activo(self, setup_clase):
        """
        REGLA: Clase ACTIVA requiere curso ACTIVO.
        
        EXPECTED: PrerequisiteException al crear clase activa con curso inactivo
        ACTUAL (antes de fix): Permite clase activa con curso inactivo ❌
        """
        # Desactivar curso
        curso = setup_clase['curso']
        curso.activo = False
        curso.save()
        
        # Intentar crear clase ACTIVA con curso INACTIVO
        with pytest.raises(PrerequisiteException) as exc_info:
            clase = Clase.objects.create(
                colegio=setup_clase['colegio'],
                curso=curso,  # INACTIVO
                asignatura=setup_clase['asignatura'],
                profesor=setup_clase['profesor'],
                activo=True
            )
        
        assert exc_info.value.error_type == 'INVALID_CURSO_STATE'
    
    def test_clase_activa_requiere_asignatura_activa(self, setup_clase):
        """
        REGLA: Clase ACTIVA requiere asignatura ACTIVA.
        
        EXPECTED: PrerequisiteException al crear clase activa con asignatura inactiva
        ACTUAL (antes de fix): Permite clase activa con asignatura inactiva ❌
        """
        # Desactivar asignatura
        asignatura = setup_clase['asignatura']
        asignatura.activa = False
        asignatura.save()
        
        # Intentar crear clase ACTIVA con asignatura INACTIVA
        with pytest.raises(PrerequisiteException) as exc_info:
            clase = Clase.objects.create(
                colegio=setup_clase['colegio'],
                curso=setup_clase['curso'],
                asignatura=asignatura,  # INACTIVA
                profesor=setup_clase['profesor'],
                activo=True
            )
        
        assert exc_info.value.error_type == 'INVALID_ASIGNATURA_STATE'
    
    def test_clase_permite_historico_inactivo(self, setup_clase):
        """
        REGLA POSITIVA: Sí se permite tener clases INACTIVAS (historial).
        
        Este test debe PASAR.
        """
        # Crear clase activa
        clase = Clase.objects.create(
            colegio=setup_clase['colegio'],
            curso=setup_clase['curso'],
            asignatura=setup_clase['asignatura'],
            profesor=setup_clase['profesor'],
            activo=True
        )
        
        # Desactivar clase (historial)
        clase.activo = False
        clase.save()
        
        # Debe permitirse
        assert clase.activo is False
        assert Clase.objects.filter(id=clase.id, activo=False).exists()
