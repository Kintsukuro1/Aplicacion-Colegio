import pytest
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from backend.apps.institucion.models import (
    Colegio, Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso, Asignatura, Clase
from backend.apps.accounts.models import Role, User, Apoderado, RelacionApoderadoEstudiante
from backend.apps.academico.models import Asistencia
from backend.apps.notificaciones.models import Notificacion
from backend.apps.core.services.academic_service import AcademicService
from backend.apps.academico.services.attendance_service import AttendanceService
from backend.apps.core.services.inspector_convivencia_api_service import InspectorConvivenciaApiService

pytestmark = pytest.mark.django_db

class TestAttendanceNotificationsCompliance(TestCase):
    """
    Suite de pruebas de cumplimiento para el sistema de alertas de asistencia y atrasos.
    Valida:
    - Despacho inmediato de alertas con alta prioridad para inasistencias y atrasos.
    - Prevención defensiva de duplicación de notificaciones.
    - Respeto a permisos individuales ('ver_asistencia') y estado activo de la relación.
    - Aislamiento multi-tenant (el apoderado del Colegio A no recibe alertas del Colegio B).
    """

    def setUp(self):
        # Configurar región, comuna, tipos
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]

        # Colegios
        self.colegio_a = Colegio.objects.get_or_create(
            rbd=11111,
            defaults={
                'nombre': 'Colegio A',
                'rut_establecimiento': '11.111.111-1',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]

        self.colegio_b = Colegio.objects.get_or_create(
            rbd=22222,
            defaults={
                'nombre': 'Colegio B',
                'rut_establecimiento': '22.222.222-2',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]

        # Roles
        self.rol_profesor, _ = Role.objects.get_or_create(nombre='Profesor')
        self.rol_estudiante, _ = Role.objects.get_or_create(nombre='Estudiante')
        self.rol_apoderado, _ = Role.objects.get_or_create(nombre='Apoderado')

        # Usuarios Colegio A
        self.profesor_a = User.objects.get_or_create(
            rut='12345678-1',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'A',
                'email': 'profesor_a@colegioa.cl',
                'rbd_colegio': self.colegio_a.rbd,
                'role': self.rol_profesor
            }
        )[0]

        self.estudiante_a = User.objects.get_or_create(
            rut='18111111-1',
            defaults={
                'nombre': 'Estudiante',
                'apellido_paterno': 'A',
                'email': 'estudiante_a@colegioa.cl',
                'rbd_colegio': self.colegio_a.rbd,
                'role': self.rol_estudiante
            }
        )[0]

        self.user_apoderado_a = User.objects.get_or_create(
            rut='9111111-1',
            defaults={
                'nombre': 'Apoderado',
                'apellido_paterno': 'A',
                'email': 'apoderado_a@test.cl',
                'rbd_colegio': self.colegio_a.rbd,
                'role': self.rol_apoderado
            }
        )[0]
        self.apoderado_a = Apoderado.objects.get_or_create(
            user=self.user_apoderado_a,
            defaults={'activo': True}
        )[0]

        # Relación Apoderado-Estudiante Activa con permiso ver_asistencia en Colegio A
        self.relacion_activa = RelacionApoderadoEstudiante.objects.get_or_create(
            apoderado=self.apoderado_a,
            estudiante=self.estudiante_a,
            defaults={
                'activa': True,
                'usar_permisos_personalizados': True,
                'puede_ver_asistencia': True
            }
        )[0]

        # Cursos y clases Colegio A
        from backend.apps.institucion.models import CicloAcademico
        self.ciclo_a = CicloAcademico.objects.get_or_create(
            nombre='2026-A',
            defaults={
                'fecha_inicio': date.today() - timedelta(days=10),
                'fecha_fin': date.today() + timedelta(days=100),
                'colegio': self.colegio_a,
                'estado': 'ACTIVO',
                'creado_por': self.profesor_a,
                'modificado_por': self.profesor_a
            }
        )[0]

        from backend.apps.institucion.models import NivelEducativo
        self.nivel = NivelEducativo.objects.get_or_create(nombre='Educación Básica')[0]

        self.curso_a = Curso.objects.get_or_create(
            nombre='1° A',
            colegio=self.colegio_a,
            ciclo_academico=self.ciclo_a,
            nivel=self.nivel,
            defaults={'activo': True}
        )[0]

        self.asignatura_a = Asignatura.objects.get_or_create(
            nombre='Lenguaje A',
            colegio=self.colegio_a,
            defaults={'horas_semanales': 4, 'activa': True}
        )[0]

        self.clase_a = Clase.objects.get_or_create(
            colegio=self.colegio_a,
            curso=self.curso_a,
            asignatura=self.asignatura_a,
            defaults={'profesor': self.profesor_a, 'activo': True}
        )[0]

        # Matrícula del Estudiante A en el Curso A
        from backend.apps.matriculas.models import Matricula
        self.matricula_a = Matricula.objects.get_or_create(
            estudiante=self.estudiante_a,
            curso=self.curso_a,
            colegio=self.colegio_a,
            ciclo_academico=self.ciclo_a,
            defaults={'estado': 'ACTIVA', 'fecha_matricula': date.today()}
        )[0]

        # Colegio B (Multi-Tenant)
        self.user_apoderado_b = User.objects.get_or_create(
            rut='9222222-2',
            defaults={
                'nombre': 'Apoderado',
                'apellido_paterno': 'B',
                'email': 'apoderado_b@test.cl',
                'rbd_colegio': self.colegio_b.rbd,
                'role': self.rol_apoderado
            }
        )[0]
        self.apoderado_b = Apoderado.objects.get_or_create(
            user=self.user_apoderado_b,
            defaults={'activo': True}
        )[0]

        # Relacionamos al apoderado B con el estudiante A (pero el apoderado B es de Colegio B)
        self.relacion_tenant_b = RelacionApoderadoEstudiante.objects.get_or_create(
            apoderado=self.apoderado_b,
            estudiante=self.estudiante_a,
            defaults={
                'activa': True,
                'usar_permisos_personalizados': True,
                'puede_ver_asistencia': True
            }
        )[0]

    def test_notificar_inasistencia_correcta(self):
        """
        Verifica que al registrar una inasistencia (AUSENTE / 'A')
        se despache inmediatamente una notificación de alta prioridad al apoderado del estudiante.
        """
        # Limpiar notificaciones previas
        Notificacion.objects.all().delete()

        # Registrar la asistencia por AcademicService
        params = {
            'user': self.profesor_a,
            'clase_id': self.clase_a.id,
            'asistencias_data': [
                {'estudiante_id': self.estudiante_a.id, 'estado': 'A'}
            ]
        }
        res = AcademicService.execute('registrar_asistencia', params)
        self.assertTrue(res['success'])

        # Verificar que se creó la asistencia en la BD
        asistencias = Asistencia.objects.filter(estudiante=self.estudiante_a, clase=self.clase_a)
        self.assertEqual(asistencias.count(), 1)
        self.assertEqual(asistencias.first().estado, 'A')

        # Verificar que se generó la notificación para el apoderado A
        notificaciones = Notificacion.objects.filter(destinatario=self.user_apoderado_a)
        self.assertEqual(notificaciones.count(), 1)
        notif = notificaciones.first()
        self.assertEqual(notif.prioridad, 'alta')
        self.assertEqual(notif.tipo, 'asistencia')
        self.assertIn("inasistencia", notif.mensaje.lower())
        self.assertIn(self.estudiante_a.get_full_name(), notif.mensaje)

    def test_notificar_atraso_correcto(self):
        """
        Verifica que al registrar un atraso ('T') por InspectorConvivenciaApiService
        se despache la notificación correspondiente con prioridad alta.
        """
        # Limpiar notificaciones
        Notificacion.objects.all().delete()

        # Registrar el atraso
        asistencia = InspectorConvivenciaApiService.registrar_atraso(
            rbd=self.colegio_a.rbd,
            clase=self.clase_a,
            estudiante=self.estudiante_a,
            fecha=str(date.today()),
            observaciones="Llegada tarde por tráfico pesado"
        )

        self.assertEqual(asistencia.estado, 'T')

        # Verificar notificación del apoderado A
        notificaciones = Notificacion.objects.filter(destinatario=self.user_apoderado_a)
        self.assertEqual(notificaciones.count(), 1)
        notif = notificaciones.first()
        self.assertEqual(notif.prioridad, 'alta')
        self.assertIn("atraso", notif.mensaje.lower())
        self.assertIn("tráfico pesado", notif.mensaje)

    def test_control_defensivo_duplicados(self):
        """
        [CUMPLIMIENTO] Verifica que registrar consecutivamente el mismo estado
        de inasistencia o atraso NO genera múltiples notificaciones (evita spam).
        """
        # Limpiar notificaciones
        Notificacion.objects.all().delete()

        # Registrar primeramente la inasistencia
        params = {
            'user': self.profesor_a,
            'clase_id': self.clase_a.id,
            'asistencias_data': [
                {'estudiante_id': self.estudiante_a.id, 'estado': 'A'}
            ]
        }
        res1 = AcademicService.execute('registrar_asistencia', params)
        self.assertTrue(res1['success'])
        self.assertEqual(Notificacion.objects.filter(destinatario=self.user_apoderado_a).count(), 1)

        # Registrar exactamente la misma inasistencia por segunda vez consecutiva
        res2 = AcademicService.execute('registrar_asistencia', params)
        self.assertTrue(res2['success'])

        # Debe seguir habiendo exactamente 1 notificación
        self.assertEqual(Notificacion.objects.filter(destinatario=self.user_apoderado_a).count(), 1)

    def test_permisos_y_relaciones_inactivas(self):
        """
        Verifica que apoderados con permisos deshabilitados o con relación inactiva
        NO reciben alertas.
        """
        # Crear un segundo apoderado para el Estudiante A
        user_apoderado_inactivo = User.objects.get_or_create(
            rut='9333333-3',
            defaults={
                'nombre': 'Apoderado',
                'apellido_paterno': 'Inactivo',
                'email': 'inactivo@test.cl',
                'rbd_colegio': self.colegio_a.rbd,
                'role': self.rol_apoderado
            }
        )[0]
        apoderado_inactivo = Apoderado.objects.get_or_create(
            user=user_apoderado_inactivo,
            defaults={'activo': True}
        )[0]

        # Relación inactiva
        rel_inactiva = RelacionApoderadoEstudiante.objects.get_or_create(
            apoderado=apoderado_inactivo,
            estudiante=self.estudiante_a,
            defaults={
                'activa': False,
                'usar_permisos_personalizados': True,
                'puede_ver_asistencia': True
            }
        )[0]

        # Crear un tercer apoderado con relación activa pero sin permiso de ver_asistencia
        user_apoderado_sin_permiso = User.objects.get_or_create(
            rut='9444444-4',
            defaults={
                'nombre': 'Apoderado',
                'apellido_paterno': 'SinPermiso',
                'email': 'sinpermiso@test.cl',
                'rbd_colegio': self.colegio_a.rbd,
                'role': self.rol_apoderado
            }
        )[0]
        apoderado_sin_permiso = Apoderado.objects.get_or_create(
            user=user_apoderado_sin_permiso,
            defaults={'activo': True}
        )[0]

        rel_sin_permiso = RelacionApoderadoEstudiante.objects.get_or_create(
            apoderado=apoderado_sin_permiso,
            estudiante=self.estudiante_a,
            defaults={
                'activa': True,
                'usar_permisos_personalizados': True,
                'puede_ver_asistencia': False
            }
        )[0]

        # Limpiar notificaciones
        Notificacion.objects.all().delete()

        # Registrar la inasistencia
        params = {
            'user': self.profesor_a,
            'clase_id': self.clase_a.id,
            'asistencias_data': [
                {'estudiante_id': self.estudiante_a.id, 'estado': 'A'}
            ]
        }
        res = AcademicService.execute('registrar_asistencia', params)
        self.assertTrue(res['success'])

        # Apoderado A (activo, con permisos) recibe
        self.assertEqual(Notificacion.objects.filter(destinatario=self.user_apoderado_a).count(), 1)
        # Apoderado inactivo NO recibe
        self.assertEqual(Notificacion.objects.filter(destinatario=user_apoderado_inactivo).count(), 0)
        # Apoderado sin permiso NO recibe
        self.assertEqual(Notificacion.objects.filter(destinatario=user_apoderado_sin_permiso).count(), 0)

    def test_aislamiento_multi_tenant(self):
        """
        [CUMPLIMIENTO] Verifica el aislamiento multi-tenant estricto.
        El apoderado B (asociado al Colegio B) NO debe recibir notificaciones
        del estudiante A del Colegio A, a pesar de estar vinculado en la base de datos por error.
        """
        # Limpiar notificaciones
        Notificacion.objects.all().delete()

        # Registrar inasistencia del Estudiante A (Colegio A)
        params = {
            'user': self.profesor_a,
            'clase_id': self.clase_a.id,
            'asistencias_data': [
                {'estudiante_id': self.estudiante_a.id, 'estado': 'A'}
            ]
        }
        res = AcademicService.execute('registrar_asistencia', params)
        self.assertTrue(res['success'])

        # Apoderado A (Colegio A) recibe la notificación
        self.assertEqual(Notificacion.objects.filter(destinatario=self.user_apoderado_a).count(), 1)
        # Apoderado B (Colegio B) NO debe recibir la notificación por seguridad multi-tenant
        self.assertEqual(Notificacion.objects.filter(destinatario=self.user_apoderado_b).count(), 0)
