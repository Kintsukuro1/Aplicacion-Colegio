import json
import pytest
from datetime import date, timedelta
from django.test import RequestFactory, TestCase
from django.utils import timezone
from unittest.mock import patch

from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso, Asignatura, Clase
from backend.apps.accounts.models import Role, User
from backend.apps.core.models import AnotacionConvivencia, JustificativoInasistencia
from backend.apps.academico.models import Asistencia
from backend.apps.auditoria.models import AuditoriaEvento
from backend.apps.core.views.inspector_convivencia.api import (
    crear_anotacion, actualizar_justificativo, registrar_atraso
)

pytestmark = pytest.mark.django_db


class TestConvivenciaCompliance(TestCase):
    """
    Suite de pruebas de cumplimiento normativo para el módulo de Convivencia Escolar.
    Verifica ficha del alumno, ciclo de vida de justificativos, registro de atrasos,
    logs de auditoría reglamentarios y aislamiento multi-tenant.
    """

    def setUp(self):
        # Datos geográficos y de establecimiento
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]

        # Colegio principal (RBD 12348)
        self.colegio = Colegio.objects.get_or_create(
            rbd=12348,
            defaults={
                'nombre': 'Colegio de Prueba Principal',
                'rut_establecimiento': '12.348.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]

        # Colegio secundario para multi-tenancy (RBD 87654)
        self.colegio_otro = Colegio.objects.get_or_create(
            rbd=87654,
            defaults={
                'nombre': 'Colegio de Prueba Secundario',
                'rut_establecimiento': '87.654.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]

        # Roles
        self.rol_inspector, _ = Role.objects.get_or_create(nombre='Inspector de Convivencia')
        self.rol_alumno, _ = Role.objects.get_or_create(nombre='Alumno')
        self.rol_apoderado, _ = Role.objects.get_or_create(nombre='Apoderado')

        # Inspectores
        self.inspector = User.objects.get_or_create(
            rut='66666666-6',
            defaults={
                'nombre': 'Inspector',
                'apellido_paterno': 'Principal',
                'email': 'inspector@test.cl',
                'rbd_colegio': self.colegio.rbd,
                'role': self.rol_inspector
            }
        )[0]
        if not self.inspector.password:
            self.inspector.set_password('testpass123')
            self.inspector.save()

        self.inspector_otro = User.objects.get_or_create(
            rut='77777777-7',
            defaults={
                'nombre': 'Inspector',
                'apellido_paterno': 'Otro',
                'email': 'inspector_otro@test.cl',
                'rbd_colegio': self.colegio_otro.rbd,
                'role': self.rol_inspector
            }
        )[0]
        if not self.inspector_otro.password:
            self.inspector_otro.set_password('testpass123')
            self.inspector_otro.save()

        # Estudiantes
        self.estudiante = User.objects.get_or_create(
            rut='11111111-1',
            defaults={
                'nombre': 'Alumno',
                'apellido_paterno': 'Uno',
                'email': 'alumno1@test.cl',
                'rbd_colegio': self.colegio.rbd,
                'role': self.rol_alumno
            }
        )[0]

        self.estudiante_otro = User.objects.get_or_create(
            rut='22222222-2',
            defaults={
                'nombre': 'Alumno',
                'apellido_paterno': 'Dos',
                'email': 'alumno2@test.cl',
                'rbd_colegio': self.colegio_otro.rbd,
                'role': self.rol_alumno
            }
        )[0]

        # Apoderados
        self.apoderado = User.objects.get_or_create(
            rut='88888888-8',
            defaults={
                'nombre': 'Apoderado',
                'apellido_paterno': 'Uno',
                'email': 'apoderado1@test.cl',
                'rbd_colegio': self.colegio.rbd,
                'role': self.rol_apoderado
            }
        )[0]

        # Ciclos, Cursos, Asignaturas y Clases
        self.ciclo = CicloAcademico.objects.create(
            nombre='2026',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.inspector,
            modificado_por=self.inspector
        )
        self.nivel = NivelEducativo.objects.get_or_create(nombre='Educación Básica')[0]
        self.curso = Curso.objects.create(
            nombre='1° Básico A',
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
            nivel=self.nivel,
            activo=True
        )
        self.asignatura = Asignatura.objects.create(
            nombre='Matemáticas',
            colegio=self.colegio,
            horas_semanales=5,
            activa=True
        )
        self.clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            activo=True
        )

    def test_crear_anotacion_conductual_y_auditoria(self):
        """
        [CUMPLIMIENTO] Verifica que un inspector pueda registrar anotaciones conductuales
        positivas/negativas y que esto genere el correspondiente log de auditoría.
        """
        factory = RequestFactory()
        payload = {
            'estudiante_id': self.estudiante.id,
            'tipo': 'NEGATIVA',
            'categoria': 'COMPORTAMIENTO',
            'descripcion': 'Falta de respeto reiterada en la sala',
            'gravedad': 3
        }

        request = factory.post(
            '/api/inspector/convivencia/anotacion/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.inspector
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Safari/17.0'

        with patch('backend.apps.core.views.inspector_convivencia.api.PolicyService.has_capability', return_value=True):
            response = crear_anotacion(request)

        self.assertEqual(response.status_code, 200)
        
        # Verificar la anotación en la base de datos
        anotacion = AnotacionConvivencia.objects.get(estudiante=self.estudiante)
        self.assertEqual(anotacion.tipo, 'NEGATIVA')
        self.assertEqual(anotacion.gravedad, 3)
        self.assertEqual(anotacion.categoria, 'COMPORTAMIENTO')
        self.assertEqual(anotacion.registrado_por, self.inspector)

        # Verificar el log de auditoría
        eventos = AuditoriaEvento.objects.filter(
            colegio_rbd=str(self.colegio.rbd),
            tabla_afectada='anotacion_convivencia',
            accion=AuditoriaEvento.CREAR
        )
        self.assertEqual(eventos.count(), 1)
        evento = eventos.first()
        self.assertEqual(evento.usuario, self.inspector)
        self.assertEqual(evento.categoria, AuditoriaEvento.CATEGORIA_ESTUDIANTES)
        self.assertEqual(evento.ip_address, '192.168.1.100')
        self.assertEqual(evento.user_agent, 'Safari/17.0')

    def test_ciclo_de_vida_justificativos_y_auditoria(self):
        """
        [CUMPLIMIENTO] Prueba el flujo de un justificativo de inasistencia desde
        PENDIENTE a APROBADO, validando su auditoría y metadatos asociados.
        """
        justificativo = JustificativoInasistencia.objects.create(
            estudiante=self.estudiante,
            colegio=self.colegio,
            fecha_ausencia=date.today(),
            motivo='Resfrío común',
            tipo='MEDICO',
            presentado_por=self.apoderado,
            estado='PENDIENTE'
        )

        factory = RequestFactory()
        payload = {
            'estado': 'APROBADO',
            'observaciones': 'Certificado médico adjunto válido.'
        }

        request = factory.post(
            f'/api/inspector/convivencia/justificativo/{justificativo.id_justificativo}/actualizar/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.inspector
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Safari/17.0'

        with patch('backend.apps.core.views.inspector_convivencia.api.PolicyService.has_capability', return_value=True):
            response = actualizar_justificativo(request, justificativo.id_justificativo)

        self.assertEqual(response.status_code, 200)

        # Verificar estado actualizado
        justificativo.refresh_from_db()
        self.assertEqual(justificativo.estado, 'APROBADO')
        self.assertEqual(justificativo.revisado_por, self.inspector)
        self.assertEqual(justificativo.observaciones_revision, 'Certificado médico adjunto válido.')

        # Verificar auditoría
        eventos = AuditoriaEvento.objects.filter(
            colegio_rbd=str(self.colegio.rbd),
            tabla_afectada='justificativo_inasistencia',
            accion=AuditoriaEvento.MODIFICAR
        )
        self.assertEqual(eventos.count(), 1)
        evento = eventos.first()
        self.assertEqual(evento.usuario, self.inspector)
        self.assertEqual(evento.categoria, AuditoriaEvento.CATEGORIA_ASISTENCIA)
        self.assertEqual(evento.ip_address, '192.168.1.100')

    def test_registrar_tardanza_asistencia_y_auditoria(self):
        """
        [CUMPLIMIENTO] Valida que al registrar un atraso de un estudiante en una clase,
        este quede registrado en el modelo de Asistencia con estado 'T' (Tardanza) y auditoría.
        """
        factory = RequestFactory()
        payload = {
            'estudiante_id': self.estudiante.id,
            'clase_id': self.clase.id,
            'fecha': date.today().isoformat(),
            'observaciones': 'Llegó 15 minutos tarde por tráfico'
        }

        request = factory.post(
            '/api/inspector/convivencia/atraso/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        request.user = self.inspector
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Safari/17.0'

        with patch('backend.apps.core.views.inspector_convivencia.api.PolicyService.has_capability', return_value=True):
            response = registrar_atraso(request)

        self.assertEqual(response.status_code, 200)

        # Verificar el registro de asistencia
        asistencia = Asistencia.objects.get(clase=self.clase, estudiante=self.estudiante, fecha=date.today())
        self.assertEqual(asistencia.estado, 'T')
        self.assertEqual(asistencia.observaciones, 'Llegó 15 minutos tarde por tráfico')

        # Verificar auditoría
        eventos = AuditoriaEvento.objects.filter(
            colegio_rbd=str(self.colegio.rbd),
            tabla_afectada='asistencia',
            accion=AuditoriaEvento.CREAR
        )
        self.assertEqual(eventos.count(), 1)
        evento = eventos.first()
        self.assertEqual(evento.usuario, self.inspector)
        self.assertEqual(evento.categoria, AuditoriaEvento.CATEGORIA_ASISTENCIA)

    def test_convivencia_multi_tenant_isolation(self):
        """
        [CUMPLIMIENTO] Verifica que inspectores de un colegio no puedan interactuar con
        registros, justificaciones o clases de alumnos pertenecientes a otro establecimiento.
        """
        factory = RequestFactory()
        
        # 1. Crear anotación para estudiante de otro colegio debe fallar (404)
        payload_anotacion = {
            'estudiante_id': self.estudiante_otro.id, # Estudiante del colegio_otro (87654)
            'tipo': 'NEGATIVA',
            'categoria': 'COMPORTAMIENTO',
            'descripcion': 'Intrusión',
            'gravedad': 1
        }
        request_anot = factory.post(
            '/api/inspector/convivencia/anotacion/',
            data=json.dumps(payload_anotacion),
            content_type='application/json'
        )
        # Inspector del colegio principal (12348)
        request_anot.user = self.inspector
        
        with patch('backend.apps.core.views.inspector_convivencia.api.PolicyService.has_capability', return_value=True):
            response_anot = crear_anotacion(request_anot)
        
        self.assertEqual(response_anot.status_code, 404)
        self.assertIn('Estudiante no encontrado', response_anot.content.decode('utf-8'))

        # 2. Revisar justificativo de otro colegio debe fallar (404)
        justificativo_otro = JustificativoInasistencia.objects.create(
            estudiante=self.estudiante_otro,
            colegio=self.colegio_otro,
            fecha_ausencia=date.today(),
            motivo='Resfrío',
            tipo='MEDICO',
            presentado_por=self.estudiante_otro, # Simplificado para el test
            estado='PENDIENTE'
        )
        
        payload_just = {
            'estado': 'APROBADO',
            'observaciones': 'Intrusión'
        }
        request_just = factory.post(
            f'/api/inspector/convivencia/justificativo/{justificativo_otro.id_justificativo}/actualizar/',
            data=json.dumps(payload_just),
            content_type='application/json'
        )
        request_just.user = self.inspector
        
        with patch('backend.apps.core.views.inspector_convivencia.api.PolicyService.has_capability', return_value=True):
            response_just = actualizar_justificativo(request_just, justificativo_otro.id_justificativo)
            
        self.assertEqual(response_just.status_code, 404)
        self.assertIn('Justificativo no encontrado', response_just.content.decode('utf-8'))
