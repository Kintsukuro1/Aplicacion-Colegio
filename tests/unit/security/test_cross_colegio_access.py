"""
Test 5.1: Acceso cross-colegio (seguridad)

Valida que usuarios de un colegio NO puedan acceder a datos
de otro colegio.

Regla de seguridad: Cada colegio debe tener sus datos aislados.
Los servicios deben filtrar por colegio automáticamente.

Patrón de tests:
- Clase 1: Tests de aislamiento de datos entre colegios
- Clase 2: Tests de validación de permisos cross-colegio
"""
import pytest
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test.client import RequestFactory
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso, Asignatura, Clase
from backend.apps.matriculas.models import Matricula
from backend.apps.academico.models import Evaluacion, Calificacion
from backend.apps.accounts.models import Role, User
from backend.apps.core.middleware.tenant import TenantMiddleware
from backend.common.tenancy import (
    reset_current_tenant_school_id,
    set_current_tenant_school_id,
)
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestAccesoCrossColegio(TestCase):
    """
    Tests de aislamiento de datos entre colegios.
    """
    
    def setUp(self):
        """Configuración: crear dos colegios independientes"""
        # Crear datos base
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]
        
        # COLEGIO 1
        self.colegio1 = Colegio.objects.get_or_create(
            rbd=12357,
            defaults={
                'nombre': 'Colegio Seguridad 1',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'colegio1@test.cl',
                'web': 'http://colegio1.cl',
                'rut_establecimiento': '12.357.000-5',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        self.admin1 = User.objects.get_or_create(
            rut='11111117-7',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Colegio1',
                'email': 'admin1@test.cl',
                'rbd_colegio': self.colegio1.rbd
            }
        )[0]
        
        self.profesor1 = User.objects.get_or_create(
            rut='12121216-5',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Colegio1',
                'email': 'profe1@test.cl',
                'rbd_colegio': self.colegio1.rbd
            }
        )[0]
        
        self.estudiante1 = User.objects.get_or_create(
            rut='13131317-7',
            defaults={
                'nombre': 'Estudiante',
                'apellido_paterno': 'Colegio1',
                'email': 'est1@test.cl',
                'rbd_colegio': self.colegio1.rbd
            }
        )[0]
        
        # COLEGIO 2
        self.colegio2 = Colegio.objects.get_or_create(
            rbd=12358,
            defaults={
                'nombre': 'Colegio Seguridad 2',
                'direccion': 'Calle Test 456',
                'telefono': '+56912345679',
                'correo': 'colegio2@test.cl',
                'web': 'http://colegio2.cl',
                'rut_establecimiento': '12.358.000-6',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]
        
        self.admin2 = User.objects.get_or_create(
            rut='11111118-8',
            defaults={
                'nombre': 'Admin',
                'apellido_paterno': 'Colegio2',
                'email': 'admin2@test.cl',
                'rbd_colegio': self.colegio2.rbd
            }
        )[0]
        
        self.profesor2 = User.objects.get_or_create(
            rut='12121217-6',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Colegio2',
                'email': 'profe2@test.cl',
                'rbd_colegio': self.colegio2.rbd
            }
        )[0]
        
        self.estudiante2 = User.objects.get_or_create(
            rut='13131318-8',
            defaults={
                'nombre': 'Estudiante',
                'apellido_paterno': 'Colegio2',
                'email': 'est2@test.cl',
                'rbd_colegio': self.colegio2.rbd
            }
        )[0]
        
        # Crear ciclos para cada colegio
        self.ciclo1 = CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio1,
            estado='ACTIVO',
            creado_por=self.admin1,
            modificado_por=self.admin1
        )
        
        self.ciclo2 = CicloAcademico.objects.create(
            nombre='2024',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio2,
            estado='ACTIVO',
            creado_por=self.admin2,
            modificado_por=self.admin2
        )
        
        # Crear nivel
        self.nivel = NivelEducativo.objects.get_or_create(
            nombre='Educación Básica'
        )[0]
        
        # Crear cursos en cada colegio
        self.curso1 = Curso.objects.create(
            nombre='5° Básico A',
            colegio=self.colegio1,
            ciclo_academico=self.ciclo1,
            nivel=self.nivel,
            activo=True
        )
        
        self.curso2 = Curso.objects.create(
            nombre='5° Básico A',
            colegio=self.colegio2,
            ciclo_academico=self.ciclo2,
            nivel=self.nivel,
            activo=True
        )

    def test_usuarios_vinculados_a_colegios_diferentes(self):
        """
        Usuarios deben estar vinculados a su colegio específico.
        """
        # Verificar vinculación correcta
        self.assertEqual(self.admin1.rbd_colegio, self.colegio1.rbd)
        self.assertEqual(self.profesor1.rbd_colegio, self.colegio1.rbd)
        self.assertEqual(self.estudiante1.rbd_colegio, self.colegio1.rbd)
        
        self.assertEqual(self.admin2.rbd_colegio, self.colegio2.rbd)
        self.assertEqual(self.profesor2.rbd_colegio, self.colegio2.rbd)
        self.assertEqual(self.estudiante2.rbd_colegio, self.colegio2.rbd)
        
        # Verificar que NO son el mismo colegio
        self.assertNotEqual(self.colegio1.rbd, self.colegio2.rbd)

    def test_cursos_filtrados_por_colegio(self):
        """
        Cursos deben filtrarse por colegio automáticamente.
        """
        # Cursos del colegio 1
        cursos_colegio1 = Curso.objects.filter(colegio=self.colegio1)
        self.assertEqual(cursos_colegio1.count(), 1)
        self.assertEqual(cursos_colegio1.first().nombre, '5° Básico A')
        
        # Cursos del colegio 2
        cursos_colegio2 = Curso.objects.filter(colegio=self.colegio2)
        self.assertEqual(cursos_colegio2.count(), 1)
        
        # Los cursos son diferentes objetos
        self.assertNotEqual(cursos_colegio1.first().pk, cursos_colegio2.first().pk)

    def test_usuario_colegio1_no_ve_datos_colegio2(self):
        """
        Usuario de colegio 1 NO debe ver cursos del colegio 2.
        """
        # Simular consulta desde colegio 1
        cursos_visibles = Curso.objects.filter(
            colegio__rbd=self.estudiante1.rbd_colegio
        )
        
        # Solo debe ver 1 curso (el de su colegio)
        self.assertEqual(cursos_visibles.count(), 1)
        self.assertEqual(cursos_visibles.first().colegio, self.colegio1)
        
        # NO debe ver el curso del colegio 2
        self.assertNotIn(self.curso2, cursos_visibles)

    def test_usuario_colegio2_no_ve_datos_colegio1(self):
        """
        Usuario de colegio 2 NO debe ver cursos del colegio 1.
        """
        # Simular consulta desde colegio 2
        cursos_visibles = Curso.objects.filter(
            colegio__rbd=self.estudiante2.rbd_colegio
        )
        
        # Solo debe ver 1 curso (el de su colegio)
        self.assertEqual(cursos_visibles.count(), 1)
        self.assertEqual(cursos_visibles.first().colegio, self.colegio2)
        
        # NO debe ver el curso del colegio 1
        self.assertNotIn(self.curso1, cursos_visibles)

    def test_matriculas_aisladas_por_colegio(self):
        """
        Matrículas deben estar aisladas por colegio.
        """
        # Crear matrículas en cada colegio
        matricula1 = Matricula.objects.create(
            colegio=self.colegio1,
            estudiante=self.estudiante1,
            curso=self.curso1,
            ciclo_academico=self.ciclo1,
            estado='ACTIVA'
        )
        
        matricula2 = Matricula.objects.create(
            colegio=self.colegio2,
            estudiante=self.estudiante2,
            curso=self.curso2,
            ciclo_academico=self.ciclo2,
            estado='ACTIVA'
        )
        
        # Verificar aislamiento
        matriculas_colegio1 = Matricula.objects.filter(colegio=self.colegio1)
        self.assertEqual(matriculas_colegio1.count(), 1)
        self.assertIn(matricula1, matriculas_colegio1)
        self.assertNotIn(matricula2, matriculas_colegio1)
        
        matriculas_colegio2 = Matricula.objects.filter(colegio=self.colegio2)
        self.assertEqual(matriculas_colegio2.count(), 1)
        self.assertIn(matricula2, matriculas_colegio2)
        self.assertNotIn(matricula1, matriculas_colegio2)

    def test_evaluaciones_aisladas_por_colegio(self):
        """
        Evaluaciones deben estar aisladas por colegio.
        """
        # Crear asignaturas y clases
        asignatura1 = Asignatura.objects.create(
            nombre='Matemáticas',
            colegio=self.colegio1,
            horas_semanales=6,
            activa=True
        )
        
        clase1 = Clase.objects.create(
            colegio=self.colegio1,
            curso=self.curso1,
            asignatura=asignatura1,
            profesor=self.profesor1,
            activo=True
        )
        
        asignatura2 = Asignatura.objects.create(
            nombre='Matemáticas',
            colegio=self.colegio2,
            horas_semanales=6,
            activa=True
        )
        
        clase2 = Clase.objects.create(
            colegio=self.colegio2,
            curso=self.curso2,
            asignatura=asignatura2,
            profesor=self.profesor2,
            activo=True
        )
        
        # Crear evaluaciones
        eval1 = Evaluacion.objects.create(
            colegio=self.colegio1,
            clase=clase1,
            nombre='Prueba 1',
            fecha_evaluacion=date.today(),
            ponderacion=100.0,
            tipo_evaluacion='sumativa'
        )
        
        eval2 = Evaluacion.objects.create(
            colegio=self.colegio2,
            clase=clase2,
            nombre='Prueba 1',
            fecha_evaluacion=date.today(),
            ponderacion=100.0,
            tipo_evaluacion='sumativa'
        )
        
        # Verificar aislamiento
        evals_colegio1 = Evaluacion.objects.filter(colegio=self.colegio1)
        self.assertEqual(evals_colegio1.count(), 1)
        self.assertIn(eval1, evals_colegio1)
        self.assertNotIn(eval2, evals_colegio1)

    def test_ciclos_academicos_separados_por_colegio(self):
        """
        Cada colegio debe tener sus propios ciclos académicos.
        """
        # Verificar que cada colegio tiene su ciclo
        ciclos_colegio1 = CicloAcademico.objects.filter(colegio=self.colegio1)
        self.assertEqual(ciclos_colegio1.count(), 1)
        self.assertEqual(ciclos_colegio1.first().nombre, '2024')
        
        ciclos_colegio2 = CicloAcademico.objects.filter(colegio=self.colegio2)
        self.assertEqual(ciclos_colegio2.count(), 1)
        self.assertEqual(ciclos_colegio2.first().nombre, '2024')
        
        # Aunque tienen el mismo nombre, son objetos diferentes
        self.assertNotEqual(
            ciclos_colegio1.first().id,
            ciclos_colegio2.first().id
        )


@pytest.mark.django_db
class TestErrorBuilderForCrossColegioAccess(TestCase):
    """
    Tests de ErrorBuilder: validar errores de acceso cross-colegio.
    """
    
    def test_error_builder_cross_colegio_access_estructura(self):
        """
        ErrorBuilder debe manejar errores de acceso cross-colegio.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            {
                'action': 'Acceso denegado a datos de otro colegio',
                'user_colegio': 12357,
                'requested_colegio': 12358,
                'resource': 'Curso'
            }
        )
        
        # Validar estructura
        self.assertIn('error_type', error)
        self.assertIn('user_message', error)
        self.assertIn('action_url', error)
        self.assertIn('context', error)

    def test_error_builder_incluye_informacion_colegios(self):
        """
        El error debe incluir información de ambos colegios.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            {
                'user_colegio': 12357,
                'user_colegio_nombre': 'Colegio 1',
                'requested_colegio': 12358,
                'requested_colegio_nombre': 'Colegio 2',
                'action': 'Intento de acceso cross-colegio'
            }
        )
        
        context = error['context']
        self.assertIn('user_colegio', context)
        self.assertIn('requested_colegio', context)

    def test_error_builder_contexto_adicional_seguridad(self):
        """
        ErrorBuilder debe permitir contexto de seguridad.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            {
                'user_rut': '13131317-7',
                'user_colegio': 12357,
                'attempted_resource': 'Curso',
                'resource_id': 123,
                'resource_colegio': 12358,
                'timestamp': '2024-02-04T10:30:00'
            }
        )
        
        context = error['context']
        self.assertIn('user_colegio', context)
        self.assertIn('resource_colegio', context)
        self.assertIn('attempted_resource', context)


@pytest.mark.django_db
class TestTenantMiddlewareAndManagers(TestCase):
    """
    Validaciones de aislamiento multi-tenant:
    - Middleware bloquea acceso cross-colegio.
    - Managers filtran automáticamente por tenant del request.
    """

    def setUp(self):
        self.factory = RequestFactory()

        region = Region.objects.create(nombre='Valparaiso')
        comuna = Comuna.objects.create(nombre='Vina del Mar', region=region)
        tipo = TipoEstablecimiento.objects.create(nombre='Particular Subvencionado')
        dependencia = DependenciaAdministrativa.objects.create(nombre='Particular')

        self.role_profesor = Role.objects.create(nombre='Profesor')
        self.role_admin_general = Role.objects.create(nombre='Administrador general')

        self.colegio_a = Colegio.objects.create(
            rbd=88001,
            rut_establecimiento='88.001.000-1',
            nombre='Colegio A',
            direccion='Direccion A',
            telefono='+56900000001',
            correo='colegioa@test.cl',
            web='http://colegioa.test',
            comuna=comuna,
            tipo_establecimiento=tipo,
            dependencia=dependencia,
        )
        self.colegio_b = Colegio.objects.create(
            rbd=88002,
            rut_establecimiento='88.002.000-2',
            nombre='Colegio B',
            direccion='Direccion B',
            telefono='+56900000002',
            correo='colegiob@test.cl',
            web='http://colegiob.test',
            comuna=comuna,
            tipo_establecimiento=tipo,
            dependencia=dependencia,
        )

        self.user_a = User.objects.create(
            email='profesor_a@test.cl',
            rut='88001000-1',
            nombre='Profesor',
            apellido_paterno='A',
            role=self.role_profesor,
            rbd_colegio=self.colegio_a.rbd,
        )
        self.admin_general = User.objects.create(
            email='admin_general@test.cl',
            rut='88002000-2',
            nombre='Admin',
            apellido_paterno='General',
            role=self.role_admin_general,
            rbd_colegio=self.colegio_a.rbd,
        )

        self.nivel = NivelEducativo.objects.create(nombre='Media Cientifico Humanista')
        self.ciclo_a = CicloAcademico.objects.create(
            colegio=self.colegio_a,
            nombre='2026',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado='ACTIVO',
            creado_por=self.user_a,
            modificado_por=self.user_a,
        )
        self.ciclo_b = CicloAcademico.objects.create(
            colegio=self.colegio_b,
            nombre='2026',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado='ACTIVO',
            creado_por=self.user_a,
            modificado_por=self.user_a,
        )

        self.curso_a = Curso.objects.create(
            colegio=self.colegio_a,
            nombre='1A',
            nivel=self.nivel,
            ciclo_academico=self.ciclo_a,
            activo=True,
        )
        self.curso_b = Curso.objects.create(
            colegio=self.colegio_b,
            nombre='1A',
            nivel=self.nivel,
            ciclo_academico=self.ciclo_b,
            activo=True,
        )

    def test_tenant_manager_filters_queryset_by_request_tenant(self):
        token = set_current_tenant_school_id(self.colegio_a.rbd)
        try:
            cursos_visibles = list(Curso.objects.order_by('id_curso'))
            self.assertEqual(len(cursos_visibles), 1)
            self.assertEqual(cursos_visibles[0].colegio_id, self.colegio_a.rbd)
            self.assertEqual(Curso.objects.all_schools().count(), 2)
        finally:
            reset_current_tenant_school_id(token)

    def test_tenant_middleware_blocks_cross_school_request(self):
        middleware = TenantMiddleware(lambda req: HttpResponse("ok"))
        request = self.factory.get('/dashboard?escuela_rbd=88002')
        request.user = self.user_a

        response = middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_tenant_middleware_applies_manager_filter_on_request(self):
        def view_count(_request):
            return HttpResponse(str(Curso.objects.count()))

        middleware = TenantMiddleware(view_count)
        request = self.factory.get('/dashboard')
        request.user = self.user_a

        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "1")

    def test_admin_general_can_use_cross_school_param_without_block(self):
        middleware = TenantMiddleware(lambda req: HttpResponse(str(Curso.objects.count())))
        request = self.factory.get('/dashboard?escuela_rbd=88002')
        request.user = self.admin_general

        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "2")
