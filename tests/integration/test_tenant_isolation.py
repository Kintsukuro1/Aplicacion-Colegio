"""Integration tests for multi-tenant data isolation."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from backend.apps.academico.models import Evaluacion
from backend.apps.academico.services.grades_service import GradesService
from backend.apps.accounts.models import PerfilEstudiante, Role, User
from backend.apps.accounts.services.student_service import StudentService
from backend.apps.comunicados.models import Comunicado
from backend.apps.comunicados.services.comunicados_service import ComunicadosService
from backend.apps.core.middleware.tenant import TenantMiddleware
from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.core.services.import_csv_service import ImportacionCSVService
from backend.apps.cursos.models import Asignatura, Clase, Curso
from backend.apps.institucion.models import CicloAcademico, Colegio, NivelEducativo
from backend.apps.matriculas.models import Matricula
from backend.apps.mensajeria.models import Conversacion, Mensaje
from backend.apps.mensajeria.services.mensajeria_service import MensajeriaService
from backend.common.exceptions import PrerequisiteException
from backend.common.tenancy import (
    reset_current_tenant_school_id,
    set_current_tenant_school_id,
)


@pytest.mark.django_db
class TenantIsolationBase(TestCase):
    """Shared setup for A/B tenant isolation scenarios."""

    @classmethod
    def setUpTestData(cls):
        cls.role_admin_escolar = Role.objects.create(nombre='Administrador escolar')
        cls.role_admin_general = Role.objects.create(nombre='Administrador general')
        cls.role_profesor = Role.objects.create(nombre='Profesor')
        cls.role_estudiante = Role.objects.create(nombre='Alumno')

        cls.colegio_a = Colegio.objects.create(
            rbd=71001,
            nombre='Colegio A',
            direccion='Direccion A',
        )
        cls.colegio_b = Colegio.objects.create(
            rbd=71002,
            nombre='Colegio B',
            direccion='Direccion B',
        )

        cls.admin_a = User.objects.create_user(
            email='admin.a@test.cl',
            password='AdminA123456!',
            nombre='Admin',
            apellido_paterno='A',
            rut='71001000-1',
            role=cls.role_admin_escolar,
            rbd_colegio=cls.colegio_a.rbd,
            is_staff=True,
        )
        cls.admin_b = User.objects.create_user(
            email='admin.b@test.cl',
            password='AdminB123456!',
            nombre='Admin',
            apellido_paterno='B',
            rut='71002000-2',
            role=cls.role_admin_escolar,
            rbd_colegio=cls.colegio_b.rbd,
            is_staff=True,
        )
        cls.admin_general = User.objects.create_user(
            email='admin.general@test.cl',
            password='AdminG123456!',
            nombre='Admin',
            apellido_paterno='General',
            rut='71003000-3',
            role=cls.role_admin_general,
            rbd_colegio=cls.colegio_a.rbd,
            is_staff=True,
        )

        cls.profesor_a = User.objects.create_user(
            email='profesor.a@test.cl',
            password='ProfesorA123!',
            nombre='Profesor',
            apellido_paterno='A',
            rut='71004000-4',
            role=cls.role_profesor,
            rbd_colegio=cls.colegio_a.rbd,
        )
        cls.profesor_b = User.objects.create_user(
            email='profesor.b@test.cl',
            password='ProfesorB123!',
            nombre='Profesor',
            apellido_paterno='B',
            rut='71005000-5',
            role=cls.role_profesor,
            rbd_colegio=cls.colegio_b.rbd,
        )

        cls.estudiante_a = User.objects.create_user(
            email='estudiante.a@test.cl',
            password='EstudianteA123!',
            nombre='Estudiante',
            apellido_paterno='A',
            rut='71006000-6',
            role=cls.role_estudiante,
            rbd_colegio=cls.colegio_a.rbd,
        )
        cls.estudiante_b = User.objects.create_user(
            email='estudiante.b@test.cl',
            password='EstudianteB123!',
            nombre='Estudiante',
            apellido_paterno='B',
            rut='71007000-7',
            role=cls.role_estudiante,
            rbd_colegio=cls.colegio_b.rbd,
        )

        cls.ciclo_a = CicloAcademico.objects.create(
            colegio=cls.colegio_a,
            nombre='2026',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado='ACTIVO',
            creado_por=cls.admin_a,
            modificado_por=cls.admin_a,
        )
        cls.ciclo_b = CicloAcademico.objects.create(
            colegio=cls.colegio_b,
            nombre='2026',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado='ACTIVO',
            creado_por=cls.admin_b,
            modificado_por=cls.admin_b,
        )

        cls.nivel = NivelEducativo.objects.create(nombre='Basica Tenant')
        cls.curso_a = Curso.objects.create(
            colegio=cls.colegio_a,
            nombre='1A',
            nivel=cls.nivel,
            ciclo_academico=cls.ciclo_a,
            activo=True,
        )
        cls.curso_b = Curso.objects.create(
            colegio=cls.colegio_b,
            nombre='1A',
            nivel=cls.nivel,
            ciclo_academico=cls.ciclo_b,
            activo=True,
        )

        cls.asignatura_a = Asignatura.objects.create(
            colegio=cls.colegio_a,
            nombre='Matematica',
            horas_semanales=6,
            activa=True,
        )
        cls.asignatura_b = Asignatura.objects.create(
            colegio=cls.colegio_b,
            nombre='Matematica',
            horas_semanales=6,
            activa=True,
        )

        cls.clase_a = Clase.objects.create(
            colegio=cls.colegio_a,
            curso=cls.curso_a,
            asignatura=cls.asignatura_a,
            profesor=cls.profesor_a,
            activo=True,
        )
        cls.clase_b = Clase.objects.create(
            colegio=cls.colegio_b,
            curso=cls.curso_b,
            asignatura=cls.asignatura_b,
            profesor=cls.profesor_b,
            activo=True,
        )

        PerfilEstudiante.objects.create(
            user=cls.estudiante_a,
            ciclo_actual=cls.ciclo_a,
            estado_academico='Activo',
        )
        PerfilEstudiante.objects.create(
            user=cls.estudiante_b,
            ciclo_actual=cls.ciclo_b,
            estado_academico='Activo',
        )

        Matricula.objects.create(
            estudiante=cls.estudiante_a,
            colegio=cls.colegio_a,
            curso=cls.curso_a,
            ciclo_academico=cls.ciclo_a,
            estado='ACTIVA',
        )
        Matricula.objects.create(
            estudiante=cls.estudiante_b,
            colegio=cls.colegio_b,
            curso=cls.curso_b,
            ciclo_academico=cls.ciclo_b,
            estado='ACTIVA',
        )

        cls.conversacion_a = Conversacion.objects.create(
            clase=cls.clase_a,
            participante1=cls.profesor_a,
            participante2=cls.estudiante_a,
        )
        cls.conversacion_b = Conversacion.objects.create(
            clase=cls.clase_b,
            participante1=cls.profesor_b,
            participante2=cls.estudiante_b,
        )

        Mensaje.objects.create(
            conversacion=cls.conversacion_a,
            emisor=cls.profesor_a,
            receptor=cls.estudiante_a,
            contenido='Mensaje A',
        )
        Mensaje.objects.create(
            conversacion=cls.conversacion_b,
            emisor=cls.profesor_b,
            receptor=cls.estudiante_b,
            contenido='Mensaje B',
        )

        cls.comunicado_a = Comunicado.objects.create(
            colegio=cls.colegio_a,
            tipo='comunicado',
            titulo='Comunicado A',
            contenido='Contenido A',
            destinatario='todos',
            publicado_por=cls.admin_a,
            activo=True,
        )
        cls.comunicado_b = Comunicado.objects.create(
            colegio=cls.colegio_b,
            tipo='comunicado',
            titulo='Comunicado B',
            contenido='Contenido B',
            destinatario='todos',
            publicado_por=cls.admin_b,
            activo=True,
        )

    @contextmanager
    def tenant_scope(self, school_id):
        token = set_current_tenant_school_id(school_id)
        try:
            yield
        finally:
            reset_current_tenant_school_id(token)

    @staticmethod
    def _build_students_csv(email: str, rut: str) -> SimpleUploadedFile:
        csv_content = (
            "email,nombre,apellido_paterno,apellido_materno,rut,password\n"
            f"{email},Importado,Alumno,Uno,{rut},PasswordSegura123!\n"
        )
        return SimpleUploadedFile(
            "estudiantes.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )


@pytest.mark.django_db
class TestCriticalServicesIsolation(TenantIsolationBase):
    def test_academic_service_profesor_cannot_create_evaluation_for_other_school_class(self):
        with self.assertRaises(PrerequisiteException) as exc_info:
            GradesService.create_evaluation(
                self.profesor_a,
                self.colegio_a,
                self.clase_b,
                'Evaluacion Cross',
                date(2026, 4, 10),
                Decimal('30.00'),
            )

        self.assertEqual(exc_info.exception.error_type, 'INVALID_RELATIONSHIP')
        self.assertFalse(Evaluacion.objects.filter(nombre='Evaluacion Cross').exists())

    def test_student_service_admin_cannot_list_students_from_other_school(self):
        with self.tenant_scope(self.colegio_a.rbd):
            cross_school = list(
                StudentService.list_students(
                    self.admin_a,
                    str(self.colegio_b.rbd),
                    User,
                    PerfilEstudiante,
                )
            )
            own_school = list(
                StudentService.list_students(
                    self.admin_a,
                    str(self.colegio_a.rbd),
                    User,
                    PerfilEstudiante,
                )
            )

        own_ids = {u.id for u in own_school}
        self.assertEqual(cross_school, [])
        self.assertIn(self.estudiante_a.id, own_ids)
        self.assertNotIn(self.estudiante_b.id, own_ids)

    def test_matriculas_cross_school_creation_is_blocked(self):
        with self.assertRaises(PrerequisiteException) as exc_info:
            Matricula.objects.create(
                estudiante=self.estudiante_a,
                colegio=self.colegio_a,
                curso=self.curso_b,
                ciclo_academico=self.ciclo_b,
                estado='ACTIVA',
            )

        self.assertEqual(exc_info.exception.error_type, 'INVALID_RELATIONSHIP')
        self.assertEqual(
            Matricula.objects.filter(
                estudiante=self.estudiante_a,
                ciclo_academico=self.ciclo_b,
            ).count(),
            0,
        )

    def test_mensajeria_school_a_messages_are_not_visible_with_school_b_tenant(self):
        with self.tenant_scope(self.colegio_b.rbd):
            mensajes = MensajeriaService.get_conversation_messages(self.conversacion_a)
        self.assertEqual(mensajes, [])

        with self.tenant_scope(self.colegio_a.rbd):
            mensajes = MensajeriaService.get_conversation_messages(self.conversacion_a)
        self.assertEqual(len(mensajes), 1)

    def test_comunicados_school_a_not_visible_for_school_b_admin(self):
        with self.tenant_scope(self.colegio_b.rbd):
            comunicados = list(ComunicadosService.get_comunicados_for_user(self.admin_b))

        comunicado_ids = {c.id_comunicado for c in comunicados}
        self.assertIn(self.comunicado_b.id_comunicado, comunicado_ids)
        self.assertNotIn(self.comunicado_a.id_comunicado, comunicado_ids)

    def test_dashboard_service_does_not_show_students_from_other_school(self):
        request = RequestFactory().get('/dashboard?pagina=gestionar_estudiantes')
        with self.tenant_scope(self.colegio_a.rbd):
            context = DashboardService.get_gestionar_estudiantes_context(
                self.admin_a,
                request,
                self.colegio_a.rbd,
            )

        estudiantes_ids = {u.id for u in context['estudiantes'].object_list}
        self.assertIn(self.estudiante_a.id, estudiantes_ids)
        self.assertNotIn(self.estudiante_b.id, estudiantes_ids)

    def test_import_csv_does_not_create_students_in_wrong_school(self):
        archivo = self._build_students_csv('importado.a@test.cl', '71008000-8')
        exitosos, fallidos, errores = ImportacionCSVService.importar_estudiantes(
            archivo,
            self.colegio_a.rbd,
        )

        self.assertEqual(exitosos, 1)
        self.assertEqual(fallidos, 0)
        self.assertEqual(errores, [])
        self.assertTrue(
            User.objects.filter(email='importado.a@test.cl', rbd_colegio=self.colegio_a.rbd).exists()
        )
        self.assertFalse(
            User.objects.filter(email='importado.a@test.cl', rbd_colegio=self.colegio_b.rbd).exists()
        )


@pytest.mark.django_db
class TestTenantMiddlewareIsolation(TenantIsolationBase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_request_with_different_school_param_returns_403(self):
        middleware = TenantMiddleware(lambda request: HttpResponse("ok"))
        request = self.factory.get(f"/dashboard?escuela_rbd={self.colegio_b.rbd}")
        request.user = self.admin_a

        response = middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_admin_general_can_access_any_school_param(self):
        middleware = TenantMiddleware(lambda request: HttpResponse(str(Curso.objects.count())))
        request = self.factory.get(f"/dashboard?escuela_rbd={self.colegio_b.rbd}")
        request.user = self.admin_general

        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "2")

    def test_unauthenticated_user_does_not_activate_tenant_filtering(self):
        middleware = TenantMiddleware(lambda request: HttpResponse(str(Curso.objects.count())))
        request = self.factory.get('/dashboard')
        request.user = AnonymousUser()

        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "2")


@pytest.mark.django_db
class TestTenantManagerIsolation(TenantIsolationBase):
    def test_model_objects_all_filters_by_active_tenant(self):
        with self.tenant_scope(self.colegio_a.rbd):
            cursos = list(Curso.objects.order_by('id_curso'))
        self.assertEqual(len(cursos), 1)
        self.assertEqual(cursos[0].colegio_id, self.colegio_a.rbd)

    def test_model_objects_all_schools_returns_all_with_tenant_active(self):
        with self.tenant_scope(self.colegio_a.rbd):
            tenant_count = Curso.objects.count()
            all_count = Curso.objects.all_schools().count()

        self.assertEqual(tenant_count, 1)
        self.assertEqual(all_count, 2)

    def test_model_objects_all_returns_all_without_tenant_context(self):
        self.assertEqual(Curso.objects.count(), 2)
