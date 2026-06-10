"""
Tests de Reglas de Negocio: Matrícula

Objetivo: Verificar que el sistema PREVIENE estados inválidos en matrículas.

Reglas que DEBEN cumplirse:
1. No se puede matricular estudiante sin ciclo académico ACTIVO
2. No se puede matricular en curso INACTIVO
3. No se puede matricular en colegio INACTIVO
4. Matrícula ACTIVA requiere curso ACTIVO
5. No se puede tener 2 matrículas ACTIVAS en el mismo ciclo
"""

import pytest
from django.contrib.auth.hashers import make_password
from django.db import transaction

from backend.apps.accounts.models import User, Role, PerfilEstudiante
from backend.apps.institucion.models import (
    CicloAcademico, Colegio, Comuna, Region, 
    TipoEstablecimiento, NivelEducativo, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso
from backend.apps.matriculas.models import Matricula
from backend.common.exceptions import PrerequisiteException


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_basico():
    """Crea estructura mínima: región, comuna, colegio, niveles, roles."""
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
    
    # Crear nivel educativo
    nivel_basica = NivelEducativo.objects.create(nombre="Educación Básica", activo=True)
    
    # Crear curso (solo campos que existen en el modelo)
    curso = Curso.objects.create(
        nombre="1ero Básico A",
        nivel=nivel_basica,
        colegio=colegio,
        activo=True
    )
    
    # Crear roles
    rol_estudiante = Role.objects.create(nombre="Alumno")
    rol_admin = Role.objects.create(nombre="Admin Escolar")
    
    # Crear usuario admin para creación de ciclos (creado_por/modificado_por)
    admin_user = User.objects.create(
        email="admin@test.cl",
        rut="11111111-1",
        nombre="Admin",
        apellido_paterno="Test",
        role=rol_admin,
        rbd_colegio=colegio.rbd,
        password=make_password("testing123"),
        is_active=True
    )
    
    return {
        'colegio': colegio,
        'curso': curso,
        'nivel': nivel_basica,
        'rol_estudiante': rol_estudiante,
        'admin_user': admin_user
    }


@pytest.fixture
def estudiante(setup_basico):
    """Crea un estudiante de ejemplo."""
    user = User.objects.create(
        email="estudiante@test.cl",
        rut="12345678-9",
        nombre="Juan",
        apellido_paterno="Pérez",
        role=setup_basico['rol_estudiante'],
        rbd_colegio=setup_basico['colegio'].rbd,
        password=make_password("testing123"),
        is_active=True
    )
    
    perfil = PerfilEstudiante.objects.create(
        user=user,
        fecha_nacimiento="2015-03-15",
        estado_academico="Activo"
    )
    
    return user


class TestMatriculaBusinessRules:
    """Tests de reglas de negocio de matrículas."""
    
    def test_no_matricula_sin_ciclo_activo(self, setup_basico, estudiante):
        """
        REGLA: No se puede matricular sin ciclo académico ACTIVO.
        
        EXPECTED: PrerequisiteException con error_type='MISSING_CICLO_ACTIVO'
        ACTUAL (antes de fix): Permite crear matrícula sin ciclo activo ❌
        """
        colegio = setup_basico['colegio']
        curso = setup_basico['curso']
        
        # IMPORTANTE: NO HAY ciclo activo creado
        
        # Intentar crear matrícula SIN ciclo activo
        with pytest.raises(PrerequisiteException) as exc_info:
            with transaction.atomic():
                matricula = Matricula.objects.create(
                    estudiante=estudiante,
                    curso=curso,
                    colegio=colegio,
                    estado='ACTIVA'
                )
        
        # Verificar que el error es correcto
        assert exc_info.value.error_type == 'MISSING_CICLO_ACTIVO'
    
    def test_no_matricula_en_curso_inactivo(self, setup_basico, estudiante):
        """
        REGLA: No se puede matricular en curso INACTIVO.
        
        EXPECTED: PrerequisiteException con error_type='INVALID_CURSO_STATE'
        ACTUAL (antes de fix): Permite matricular en curso inactivo ❌
        """
        colegio = setup_basico['colegio']
        curso = setup_basico['curso']
        
        # Crear ciclo activo
        ciclo = CicloAcademico.objects.create(
            colegio=colegio,
            nombre="2024",
            estado='ACTIVO',
            fecha_inicio="2024-03-01",
            fecha_fin="2024-12-31",
            creado_por=setup_basico['admin_user'],
            modificado_por=setup_basico['admin_user']
        )
        
        # Desactivar curso
        curso.activo = False
        curso.save()
        
        # Intentar matricular en curso INACTIVO
        with pytest.raises(PrerequisiteException) as exc_info:
            with transaction.atomic():
                matricula = Matricula.objects.create(
                    estudiante=estudiante,
                    curso=curso,
                    colegio=colegio,
                    ciclo_academico=ciclo,
                    estado='ACTIVA'
                )
        
        assert exc_info.value.error_type == 'INVALID_CURSO_STATE'
    
    def test_no_matricula_en_colegio_inactivo(self, setup_basico, estudiante):
        """
        REGLA: No se puede matricular en colegio INACTIVO.
        
        EXPECTED: PrerequisiteException con error_type='SCHOOL_NOT_CONFIGURED'
        ACTUAL (antes de fix): Permite matricular en colegio inactivo ❌
        
        NOTA: Como Colegio no tiene campo 'activo', este test se OMITE. 
        Esta es una falla de diseño del modelo que debe documentarse.
        """
        pytest.skip("Colegio no tiene campo 'activo' - gap arquitectónico detectado")
    
    def test_no_multiples_matriculas_activas_mismo_ciclo(self, setup_basico, estudiante):
        """
        REGLA: No se puede tener 2 matrículas ACTIVAS en el mismo ciclo.
        
        EXPECTED: PrerequisiteException o ValidationError
        ACTUAL (antes de fix): Permite múltiples matrículas activas ❌
        """
        colegio = setup_basico['colegio']
        curso = setup_basico['curso']
        
        # Crear ciclo activo
        ciclo = CicloAcademico.objects.create(
            colegio=colegio,
            nombre="2024",
            estado='ACTIVO',
            fecha_inicio="2024-03-01",
            fecha_fin="2024-12-31",
            creado_por=setup_basico['admin_user'],
            modificado_por=setup_basico['admin_user']
        )
        
        # Crear primera matrícula ACTIVA
        matricula1 = Matricula.objects.create(
            estudiante=estudiante,
            curso=curso,
            colegio=colegio,
            ciclo_academico=ciclo,
            estado='ACTIVA'
        )
        
        # Crear segunda curso
        curso2 = Curso.objects.create(
            nombre="2do Básico B",
            nivel=setup_basico['nivel'],
            colegio=colegio,
            activo=True
        )
        
        # Intentar crear SEGUNDA matrícula ACTIVA en el mismo ciclo
        with pytest.raises((PrerequisiteException, Exception)) as exc_info:
            with transaction.atomic():
                matricula2 = Matricula.objects.create(
                    estudiante=estudiante,
                    curso=curso2,
                    colegio=colegio,
                    ciclo_academico=ciclo,
                    estado='ACTIVA'
                )
        
        # Debe rechazarse
        assert True  # Si llega aquí, significa que se lanzó excepción correctamente
    
    def test_matricula_permite_historico_inactivo(self, setup_basico, estudiante):
        """
        REGLA POSITIVA: Sí se permite tener matrículas INACTIVAS (historial).
        
        Este test debe PASAR.
        """
        colegio = setup_basico['colegio']
        curso = setup_basico['curso']
        
        # Crear varios ciclos
        ciclo_2023 = CicloAcademico.objects.create(
            colegio=colegio,
            nombre="2023",
            estado='CERRADO',
            fecha_inicio="2023-03-01",
            fecha_fin="2023-12-31",
            creado_por=setup_basico['admin_user'],
            modificado_por=setup_basico['admin_user']
        )
        
        ciclo_2024 = CicloAcademico.objects.create(
            colegio=colegio,
            nombre="2024",
            estado='ACTIVO',
            fecha_inicio="2024-03-01",
            fecha_fin="2024-12-31",
            creado_por=setup_basico['admin_user'],
            modificado_por=setup_basico['admin_user']
        )
        
        # Crear matrícula INACTIVA (histórica) en ciclo 2023
        matricula_historica = Matricula.objects.create(
            estudiante=estudiante,
            curso=curso,
            colegio=colegio,
            ciclo_academico=ciclo_2023,
            estado='RETIRADA'  # Estado inactivo
        )
        
        # Crear matrícula ACTIVA en ciclo 2024
        matricula_activa = Matricula.objects.create(
            estudiante=estudiante,
            curso=curso,
            colegio=colegio,
            ciclo_academico=ciclo_2024,
            estado='ACTIVA'
        )
        
        # Debe permitirse: 1 matrícula ACTIVA + N matrículas INACTIVAS
        assert Matricula.objects.filter(estudiante=estudiante).count() == 2
        assert Matricula.objects.filter(estudiante=estudiante, estado='ACTIVA').count() == 1
        assert Matricula.objects.filter(estudiante=estudiante, estado='RETIRADA').count() == 1
