"""
Tests for Data Repair Service - Fase 2: Corrección Controlada de Datos

Valida que:
1. El servicio NUNCA borra registros
2. Solo marca como inactivo, suspende o corrige estados
3. Todas las correcciones son auditables
4. dry_run no persiste cambios
5. Todas las categorías de problemas son corregidas correctamente
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date

from backend.apps.core.services.data_repair_service import DataRepairService
from backend.apps.institucion.models import Colegio, CicloAcademico, Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
from backend.apps.cursos.models import Curso, Clase, NivelEducativo, Asignatura
from backend.apps.matriculas.models import Matricula
from backend.apps.accounts.models import PerfilEstudiante, Role
from backend.common.exceptions import PrerequisiteException

User = get_user_model()


@pytest.fixture
def setup_base_data(db):
    """Fixture que crea datos base necesarios para los tests"""
    # Crear usuario admin para audit trails
    admin_role = Role.objects.create(
        nombre='Administrador'
    )
    admin = User.objects.create_user(
        rut='11111111-1',
        nombre='Admin',
        apellido_paterno='Test',
        email='admin@test.cl',
        password='test123',
        role=admin_role
    )
    
    # Crear región y comuna
    region = Region.objects.create(nombre='Metropolitana')
    comuna = Comuna.objects.create(nombre='Santiago', region=region)
    
    # Crear tipo establecimiento y dependencia
    tipo_establecimiento = TipoEstablecimiento.objects.create(nombre='Colegio')
    dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
    
    # Crear colegio
    colegio = Colegio.objects.create(
        rbd=12345,
        rut_establecimiento='76123456-7',
        nombre='Colegio Test',
        direccion='Test 123',
        comuna=comuna,
        tipo_establecimiento=tipo_establecimiento,
        dependencia=dependencia,
        correo='colegio@test.cl',
        telefono='123456789'
    )
    
    # Crear ciclos académicos
    ciclo_activo = CicloAcademico.objects.create(
        nombre='2024',
        colegio=colegio,
        fecha_inicio=date(2024, 3, 1),
        fecha_fin=date(2024, 12, 31),
        estado='ACTIVO',
        creado_por=admin,
        modificado_por=admin
    )
    
    ciclo_inactivo = CicloAcademico.objects.create(
        nombre='2023',
        colegio=colegio,
        fecha_inicio=date(2023, 3, 1),
        fecha_fin=date(2023, 12, 31),
        estado='CERRADO',
        creado_por=admin,
        modificado_por=admin
    )
    
    # Crear nivel educativo
    nivel = NivelEducativo.objects.create(
        nombre='Primero Básico'
    )
    
    # Crear roles
    role_estudiante = Role.objects.create(nombre='Estudiante')
    role_profesor = Role.objects.create(nombre='Profesor')
    
    return {
        'admin': admin,
        'colegio': colegio,
        'ciclo_activo': ciclo_activo,
        'ciclo_inactivo': ciclo_inactivo,
        'nivel': nivel,
        'role_estudiante': role_estudiante,
        'role_profesor': role_profesor,
        'comuna': comuna
    }


@pytest.mark.django_db
class TestDataRepairServiceMatriculas:
    """Tests para corrección de matrículas inválidas"""
    
    def test_repair_matricula_curso_inactivo(self, setup_base_data):
        """Test: El sistema previene matrícula activa con curso inactivo."""
        data = setup_base_data
        
        # Crear curso INACTIVO con ciclo activo
        curso = Curso.objects.create(
            nombre='1° Básico A',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=data['ciclo_activo'],
            activo=False  # CURSO INACTIVO
        )
        
        # Crear estudiante
        estudiante = User.objects.create_user(
            rut='22222222-2',
            nombre='Juan',
            apellido_paterno='Pérez',
            email='juan@test.cl',
            password='test123',
            role=data['role_estudiante'],
            rbd_colegio=data['colegio'].rbd
        )
        
        with pytest.raises(PrerequisiteException):
            Matricula.objects.create(
                estudiante=estudiante,
                colegio=data['colegio'],
                curso=curso,
                ciclo_academico=data['ciclo_activo'],
                estado='ACTIVA'
            )
    
    def test_repair_matricula_ciclo_invalido(self, setup_base_data):
        """Test: Matrícula activa con ciclo no ACTIVO debe suspenderse"""
        data = setup_base_data
        
        # Crear curso con ciclo INACTIVO
        curso = Curso.objects.create(
            nombre='1° Básico B',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=data['ciclo_inactivo'],  # CICLO CERRADO
            activo=True
        )
        
        estudiante = User.objects.create_user(
            rut='33333333-3',
            nombre='María',
            apellido_paterno='González',
            email='maria@test.cl',
            password='test123',
            role=data['role_estudiante'],
            rbd_colegio=data['colegio'].rbd
        )
        
        # Matrícula ACTIVA con ciclo CERRADO
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            colegio=data['colegio'],
            curso=curso,
            ciclo_academico=data['ciclo_inactivo'],  # CICLO NO ACTIVO
            estado='ACTIVA'
        )
        
        service = DataRepairService()
        report = service.repair_all(dry_run=False)
        
        matricula.refresh_from_db()
        assert matricula.estado == 'SUSPENDIDA'
        assert not Matricula.objects.filter(id=matricula.id).exclude(estado='SUSPENDIDA').exists()
    
    def test_repair_matricula_sin_curso(self, setup_base_data):
        """Test: Matrícula activa sin curso debe suspenderse"""
        data = setup_base_data
        
        estudiante = User.objects.create_user(
            rut='44444444-4',
            nombre='Pedro',
            apellido_paterno='López',
            email='pedro@test.cl',
            password='test123',
            role=data['role_estudiante'],
            rbd_colegio=data['colegio'].rbd
        )
        
        # Matrícula sin curso
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            colegio=data['colegio'],
            curso=None,  # SIN CURSO
            ciclo_academico=data['ciclo_activo'],
            estado='ACTIVA'
        )
        
        service = DataRepairService()
        report = service.repair_all(dry_run=False)
        
        matricula.refresh_from_db()
        assert matricula.estado == 'SUSPENDIDA'


@pytest.mark.django_db
class TestDataRepairServiceCursos:
    """Tests para corrección de cursos inválidos"""
    
    def test_repair_curso_ciclo_invalido(self, setup_base_data):
        """Test: Curso activo con ciclo no ACTIVO debe desactivarse"""
        data = setup_base_data
        
        # Curso ACTIVO con ciclo CERRADO
        curso = Curso.objects.create(
            nombre='2° Básico A',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=data['ciclo_inactivo'],  # CICLO CERRADO
            activo=True  # CURSO ACTIVO - ESTADO INVÁLIDO
        )
        
        service = DataRepairService()
        report = service.repair_all(dry_run=False)
        
        curso.refresh_from_db()
        assert curso.activo == False
        assert report['total_corrections'] >= 1
        
        # Validar que NO fue borrado
        assert Curso.objects.filter(id_curso=curso.id_curso).exists()
    
    def test_repair_curso_sin_ciclo(self, setup_base_data):
        """Test: Curso activo sin ciclo debe desactivarse"""
        data = setup_base_data
        
        curso = Curso.objects.create(
            nombre='3° Básico A',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=None,  # SIN CICLO
            activo=True
        )
        
        service = DataRepairService()
        report = service.repair_all(dry_run=False)
        
        curso.refresh_from_db()
        assert curso.activo == False


@pytest.mark.django_db
class TestDataRepairServiceClases:
    """Tests para corrección de clases inválidas"""
    
    def test_repair_clase_curso_inactivo(self, setup_base_data):
        """Test: El sistema previene clase activa con curso inactivo."""
        data = setup_base_data
        
        # Curso inactivo
        curso = Curso.objects.create(
            nombre='4° Básico A',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=data['ciclo_activo'],
            activo=False  # CURSO INACTIVO
        )
        
        # Profesor
        profesor = User.objects.create_user(
            rut='55555555-5',
            nombre='Carlos',
            apellido_paterno='Profesor',
            email='carlos@test.cl',
            password='test123',
            role=data['role_profesor'],
            rbd_colegio=data['colegio'].rbd
        )
        
        # Asignatura
        asignatura = Asignatura.objects.create(nombre='Matemáticas', colegio=data['colegio'])
        
        with pytest.raises(PrerequisiteException):
            Clase.objects.create(
                curso=curso,
                asignatura=asignatura,
                profesor=profesor,
                colegio=data['colegio'],
                activo=True
            )
    
    def test_repair_clase_profesor_inactivo(self, setup_base_data):
        """Test: El sistema previene clase activa con profesor inactivo."""
        data = setup_base_data
        
        curso = Curso.objects.create(
            nombre='5° Básico A',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=data['ciclo_activo'],
            activo=True
        )
        
        # Profesor INACTIVO
        profesor = User.objects.create_user(
            rut='66666666-6',
            nombre='Ana',
            apellido_paterno='Profesora',
            email='ana@test.cl',
            password='test123',
            role=data['role_profesor'],
            rbd_colegio=data['colegio'].rbd,
            is_active=False  # PROFESOR INACTIVO
        )
        
        asignatura = Asignatura.objects.create(nombre='Lenguaje', colegio=data['colegio'])
        
        with pytest.raises(PrerequisiteException):
            Clase.objects.create(
                curso=curso,
                asignatura=asignatura,
                profesor=profesor,
                colegio=data['colegio'],
                activo=True
            )


@pytest.mark.django_db
class TestDataRepairServicePerfiles:
    """Tests para corrección de perfiles de estudiante inválidos"""
    
    def test_repair_perfil_ciclo_invalido(self, setup_base_data):
        """Test: Perfil activo con ciclo no ACTIVO debe suspenderse"""
        data = setup_base_data
        
        estudiante = User.objects.create_user(
            rut='77777777-7',
            nombre='Luis',
            apellido_paterno='Estudiante',
            email='luis@test.cl',
            password='test123',
            role=data['role_estudiante'],
            rbd_colegio=data['colegio'].rbd
        )
        
        # Perfil ACTIVO con ciclo CERRADO
        perfil = PerfilEstudiante.objects.create(
            user=estudiante,
            estado_academico='Activo',  # ACTIVO
            ciclo_actual=data['ciclo_inactivo']  # CICLO CERRADO
        )
        
        service = DataRepairService()
        report = service.repair_all(dry_run=False)
        
        perfil.refresh_from_db()
        assert perfil.estado_academico == 'Suspendido'
        
        # Validar que NO fue borrado
        assert PerfilEstudiante.objects.filter(id=perfil.id).exists()
    
    def test_repair_perfil_sin_ciclo(self, setup_base_data):
        """Test: Perfil activo sin ciclo debe suspenderse"""
        data = setup_base_data
        
        estudiante = User.objects.create_user(
            rut='88888888-8',
            nombre='Sofía',
            apellido_paterno='Estudiante',
            email='sofia@test.cl',
            password='test123',
            role=data['role_estudiante'],
            rbd_colegio=data['colegio'].rbd
        )
        
        perfil = PerfilEstudiante.objects.create(
            user=estudiante,
            estado_academico='Activo',
            ciclo_actual=None  # SIN CICLO
        )
        
        service = DataRepairService()
        report = service.repair_all(dry_run=False)
        
        perfil.refresh_from_db()
        assert perfil.estado_academico == 'Suspendido'
    
    def test_repair_perfil_user_inactivo(self, setup_base_data):
        """Test: Perfil activo con usuario inactivo debe suspenderse"""
        data = setup_base_data
        
        estudiante = User.objects.create_user(
            rut='99999999-9',
            nombre='Diego',
            apellido_paterno='Estudiante',
            email='diego@test.cl',
            password='test123',
            role=data['role_estudiante'],
            rbd_colegio=data['colegio'].rbd,
            is_active=False  # USUARIO INACTIVO
        )
        
        perfil = PerfilEstudiante.objects.create(
            user=estudiante,
            estado_academico='Activo',  # PERFIL ACTIVO - ESTADO INVÁLIDO
            ciclo_actual=data['ciclo_activo']
        )
        
        service = DataRepairService()
        report = service.repair_all(dry_run=False)
        
        perfil.refresh_from_db()
        assert perfil.estado_academico == 'Suspendido'


@pytest.mark.django_db
class TestDataRepairServiceDryRun:
    """Tests para validar que dry_run NO persiste cambios"""
    
    def test_dry_run_no_persiste_cambios(self, setup_base_data):
        """Test: dry_run debe reportar cambios sin persistirlos"""
        data = setup_base_data
        
        # Crear curso inválido
        curso = Curso.objects.create(
            nombre='Curso Test',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=data['ciclo_inactivo'],  # CICLO CERRADO
            activo=True  # ACTIVO - INVÁLIDO
        )
        
        # Ejecutar en modo dry_run
        service = DataRepairService()
        report = service.repair_all(dry_run=True)
        
        # Validar que reporta correcciones
        assert report['total_corrections'] >= 1
        assert report['dry_run'] == True
        
        # Validar que NO se persistió el cambio
        curso.refresh_from_db()
        assert curso.activo == True  # TODAVÍA ACTIVO
    
    def test_dry_run_multiple_categorias(self, setup_base_data):
        """Test: dry_run debe reportar todas las categorías sin persistir"""
        data = setup_base_data
        
        # Crear múltiples problemas
        curso_invalido = Curso.objects.create(
            nombre='Curso Invalido',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=data['ciclo_inactivo'],
            activo=True
        )
        
        estudiante = User.objects.create_user(
            rut='10101010-1',
            nombre='Test',
            apellido_paterno='Student',
            email='teststudent@test.cl',
            password='test123',
            role=data['role_estudiante'],
            rbd_colegio=data['colegio'].rbd
        )
        
        perfil_invalido = PerfilEstudiante.objects.create(
            user=estudiante,
            estado_academico='Activo',
            ciclo_actual=None
        )
        
        # Ejecutar dry_run
        service = DataRepairService()
        report = service.repair_all(dry_run=True)
        
        # Validar que reporta múltiples correcciones
        assert report['total_corrections'] >= 2
        assert report['dry_run'] == True
        
        # Validar que NINGÚN cambio se persistió
        curso_invalido.refresh_from_db()
        assert curso_invalido.activo == True
        
        perfil_invalido.refresh_from_db()
        assert perfil_invalido.estado_academico == 'Activo'


@pytest.mark.django_db
class TestDataRepairServiceNeverDelete:
    """Tests para validar que NUNCA se borran registros"""
    
    def test_never_delete_matricula(self, setup_base_data):
        """Test: Estados inválidos se previenen en creación (sin borrados)."""
        data = setup_base_data
        
        curso = Curso.objects.create(
            nombre='Curso',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=data['ciclo_activo'],
            activo=False
        )
        
        estudiante = User.objects.create_user(
            rut='11111111-2',
            nombre='Test',
            apellido_paterno='Delete',
            email='testdelete@test.cl',
            password='test123',
            role=data['role_estudiante'],
            rbd_colegio=data['colegio'].rbd
        )
        
        with pytest.raises(PrerequisiteException):
            Matricula.objects.create(
                estudiante=estudiante,
                colegio=data['colegio'],
                curso=curso,
                ciclo_academico=data['ciclo_activo'],
                estado='ACTIVA'
            )
    
    def test_count_records_before_after(self, setup_base_data):
        """Test: El conteo de registros debe ser idéntico antes y después"""
        data = setup_base_data
        
        # Crear varios registros inválidos
        curso1 = Curso.objects.create(
            nombre='Curso 1',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=data['ciclo_inactivo'],
            activo=True
        )
        
        curso2 = Curso.objects.create(
            nombre='Curso 2',
            nivel=data['nivel'],
            colegio=data['colegio'],
            ciclo_academico=None,
            activo=True
        )
        
        # Contar antes
        count_before = Curso.objects.count()
        
        # Ejecutar reparación
        service = DataRepairService()
        service.repair_all(dry_run=False)
        
        # Contar después
        count_after = Curso.objects.count()
        
        # DEBE SER IDÉNTICO
        assert count_before == count_after
