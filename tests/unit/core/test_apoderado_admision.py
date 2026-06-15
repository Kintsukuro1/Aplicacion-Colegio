"""
Suite de pruebas unitarias — Módulo de Admisión y Matrícula 100% Online
Fase 3, Ítem 1.

Verifica:
1. Creación de postulación con cupos disponibles (estado PENDIENTE).
2. Cálculo dinámico de cola y asignación a Lista de Espera si cupos llenos (>=3).
3. Firma electrónica simple de contrato legal educacional, hash SHA-256 y matriculación.
4. Protección de aislamiento multi-tenant estricto para apoderados y colegios.
"""

import json
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.utils import timezone

from backend.apps.accounts.models import Role, User, Apoderado
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa,
)
from backend.apps.cursos.models import Curso
from backend.apps.matriculas.models import SolicitudAdmision, ContratoServicioEducacional, Matricula
from backend.apps.core.services.apoderado_api_service import ApoderadoApiService
from backend.apps.core.views.apoderado.api import (
    crear_solicitud_admision,
    firmar_contrato,
)

pytestmark = pytest.mark.django_db


class TestApoderadoAdmision(TestCase):
    """
    Suite de pruebas unitarias y de integración para validar el flujo
    de postulaciones en línea, listas de espera y firmas digitales de contratos.
    """

    def setUp(self):
        # ── Geographic data ──────────────────────────────────
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago', defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]

        # ── School A ─────────────────────────────────────────
        self.colegio_a = Colegio.objects.get_or_create(
            rbd=77001,
            defaults={
                'nombre': 'Colegio Admisión A',
                'rut_establecimiento': '77.001.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia,
            },
        )[0]

        # ── School B ─────────────────────────────────────────
        self.colegio_b = Colegio.objects.get_or_create(
            rbd=77002,
            defaults={
                'nombre': 'Colegio Admisión B',
                'rut_establecimiento': '77.002.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia,
            },
        )[0]

        # ── Roles ────────────────────────────────────────────
        self.role_apoderado = Role.objects.get_or_create(
            nombre='apoderado'
        )[0]
        self.role_student = Role.objects.get_or_create(
            nombre='estudiante'
        )[0]

        # ── Parent users ─────────────────────────────────────
        self.apoderado_a = User.objects.create_user(
            email='apod_a@colegio.cl',
            rut='15555555-1',
            username='apod_a', password='test1234',
            nombre='Carlos', apellido_paterno='Gómez',
            rbd_colegio=self.colegio_a.rbd,
        )
        self.apoderado_a.role = self.role_apoderado
        self.apoderado_a.save()
        self.perfil_apod_a = Apoderado.objects.create(user=self.apoderado_a, activo=True)

        self.apoderado_b = User.objects.create_user(
            email='apod_b@colegio.cl',
            rut='15555555-2',
            username='apod_b', password='test1234',
            nombre='María', apellido_paterno='López',
            rbd_colegio=self.colegio_b.rbd,
        )
        self.apoderado_b.role = self.role_apoderado
        self.apoderado_b.save()
        self.perfil_apod_b = Apoderado.objects.create(user=self.apoderado_b, activo=True)

        # ── Cycles, levels and courses ───────────────────────
        self.ciclo_a = CicloAcademico.objects.create(
            colegio=self.colegio_a, nombre='2026-AdmA',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 15),
            estado='ACTIVO',
            creado_por=self.apoderado_a,
            modificado_por=self.apoderado_a,
        )
        
        self.ciclo_b = CicloAcademico.objects.create(
            colegio=self.colegio_b, nombre='2026-AdmB',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 15),
            estado='ACTIVO',
            creado_por=self.apoderado_b,
            modificado_por=self.apoderado_b,
        )

        nivel = NivelEducativo.objects.get_or_create(nombre='Enseñanza Básica')[0]
        
        self.curso_a = Curso.objects.create(
            nombre='1A-Básico', colegio=self.colegio_a,
            nivel=nivel, activo=True,
            ciclo_academico=self.ciclo_a,
        )
        
        self.curso_b = Curso.objects.create(
            nombre='1B-Básico', colegio=self.colegio_b,
            nivel=nivel, activo=True,
            ciclo_academico=self.ciclo_b,
        )

        self.factory = RequestFactory()

    # ── Helpers ──────────────────────────────────────────────

    def _build_post_request(self, url, user, data, is_multipart=False):
        if is_multipart:
            request = self.factory.post(url, data=data)
        else:
            request = self.factory.post(
                url,
                data=json.dumps(data),
                content_type='application/json',
            )
        request.user = user
        request.session = {}
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'PytestAgent'
        return request

    # ──────────────────────────────────────────────────────────
    # TEST 1: Postulación con cupos disponibles (PENDIENTE)
    # ──────────────────────────────────────────────────────────

    def test_postulacion_con_cupo_libre(self):
        """
        Una postulación ingresa con estado PENDIENTE si hay
        cupos disponibles en el curso correspondiente.
        """
        request = self._build_post_request('/api/apoderado/admisiones/solicitar/', self.apoderado_a, {
            'curso_id': self.curso_a.id_curso,
            'ciclo_id': self.ciclo_a.id,
            'nombre_estudiante': 'Mateo',
            'apellido_paterno_estudiante': 'Gómez',
            'apellido_materno_estudiante': 'Soto',
            'rut_estudiante': '25.666.777-K',
            'fecha_nacimiento_estudiante': '2020-05-10',
            'genero_estudiante': 'M',
            'direccion_hogar': 'Av Providencia 1234, Santiago',
            'telefono_contacto': '+56 9 8888 7777',
            'parentesco': 'PADRE',
        }, is_multipart=True)

        response = crear_solicitud_admision(request)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['estado'], 'PENDIENTE')
        self.assertIsNone(data['posicion'])

        # Verificar actualización de ficha familiar en perfil_apoderado
        self.perfil_apod_a.refresh_from_db()
        self.assertEqual(self.perfil_apod_a.direccion, 'Av Providencia 1234, Santiago')
        self.assertEqual(self.perfil_apod_a.telefono, '+56 9 8888 7777')

    # ──────────────────────────────────────────────────────────
    # TEST 2: Lista de Espera Dinámica (Límite >=3)
    # ──────────────────────────────────────────────────────────

    def test_lista_de_espera_dinamica(self):
        """
        Si el curso ya posee 3 matrículas activas, la nueva postulación
        ingresa automáticamente en EN_LISTA_ESPERA calculando su cola.
        """
        # Crear 3 matrículas activas artificialmente
        for i in range(3):
            estudiante_dummy = User.objects.create_user(
                email=f"dummy_{i}@colegio.cl",
                rut=f"22222222-{i}",
                username=f"dummy_usr_{i}", password='pwd',
                nombre='Est', apellido_paterno='Dummy',
                rbd_colegio=self.colegio_a.rbd
            )
            estudiante_dummy.role = self.role_student
            estudiante_dummy.save()
            
            Matricula.objects.create(
                estudiante=estudiante_dummy,
                colegio=self.colegio_a,
                curso=self.curso_a,
                estado='ACTIVA',
                ciclo_academico=self.ciclo_a,
                valor_matricula=150000,
                valor_mensual=250000
            )

        # Primera postulación en lista de espera
        request1 = self._build_post_request('/api/apoderado/admisiones/solicitar/', self.apoderado_a, {
            'curso_id': self.curso_a.id_curso,
            'ciclo_id': self.ciclo_a.id,
            'nombre_estudiante': 'Sofía',
            'apellido_paterno_estudiante': 'Gómez',
            'apellido_materno_estudiante': 'Soto',
            'rut_estudiante': '25.666.888-0',
            'fecha_nacimiento_estudiante': '2020-06-12',
            'genero_estudiante': 'F',
            'direccion_hogar': 'Av Providencia 1234',
            'telefono_contacto': '+56988887777',
            'parentesco': 'PADRE',
        }, is_multipart=True)
        
        response1 = crear_solicitud_admision(request1)
        self.assertEqual(response1.status_code, 200)
        data1 = json.loads(response1.content)
        self.assertEqual(data1['estado'], 'EN_LISTA_ESPERA')
        self.assertEqual(data1['posicion'], 1)

        # Segunda postulación en lista de espera
        request2 = self._build_post_request('/api/apoderado/admisiones/solicitar/', self.apoderado_a, {
            'curso_id': self.curso_a.id_curso,
            'ciclo_id': self.ciclo_a.id,
            'nombre_estudiante': 'Pedro',
            'apellido_paterno_estudiante': 'Gómez',
            'apellido_materno_estudiante': 'Soto',
            'rut_estudiante': '25.666.999-1',
            'fecha_nacimiento_estudiante': '2020-07-15',
            'genero_estudiante': 'M',
            'parentesco': 'PADRE',
        }, is_multipart=True)
        
        response2 = crear_solicitud_admision(request2)
        self.assertEqual(response2.status_code, 200)
        data2 = json.loads(response2.content)
        self.assertEqual(data2['estado'], 'EN_LISTA_ESPERA')
        self.assertEqual(data2['posicion'], 2)

    # ──────────────────────────────────────────────────────────
    # TEST 3: Firma Electrónica Simple y Matriculación
    # ──────────────────────────────────────────────────────────

    def test_firma_contrato_y_matricula_automatica(self):
        """
        Al firmar un contrato educacional aceptado vía firma electrónica simple,
        se valida la integridad, se crea el estudiante y su matrícula activa.
        """
        # 1. Crear solicitud aceptada
        solicitud = SolicitudAdmision.objects.create(
            colegio=self.colegio_a,
            apoderado=self.apoderado_a,
            ciclo_academico=self.ciclo_a,
            curso_postulado=self.curso_a,
            nombre_estudiante='Tomás',
            apellido_paterno_estudiante='Gómez',
            apellido_materno_estudiante='Miranda',
            rut_estudiante='26.111.222-3',
            parentesco='PADRE',
            estado='ACEPTADA'
        )

        # 2. Firmar contrato
        request = self._build_post_request('/api/apoderado/admisiones/firmar-contrato/', self.apoderado_a, {
            'solicitud_id': solicitud.id_solicitud,
            'rut_firmante': '15.555.555-1',
        })
        response = firmar_contrato(request)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIsNotNone(data['hash'])
        self.assertIsNotNone(data['token'])

        # 3. Verificar estado en Base de Datos
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'FIRMADA')
        self.assertIsNotNone(solicitud.estudiante)

        # Verificar que el usuario estudiante existe
        student_user = solicitud.estudiante
        self.assertEqual(student_user.rut, '26.111.222-3')
        self.assertEqual(student_user.nombre, 'Tomás')
        
        # Verificar perfil de estudiante
        self.assertEqual(student_user.perfil_estudiante.estado_academico, 'Activo')

        # Verificar matrícula activa oficial
        matricula = Matricula.objects.get(estudiante=student_user, ciclo_academico=self.ciclo_a)
        self.assertEqual(matricula.estado, 'ACTIVA')
        self.assertEqual(matricula.valor_matricula, Decimal('150000'))

        # Verificar contrato firmado
        contrato = ContratoServicioEducacional.objects.get(solicitud=solicitud)
        self.assertTrue(contrato.firmado)
        self.assertEqual(contrato.rut_firmante, '15.555.555-1')
        self.assertEqual(contrato.firma_hash, data['hash'])
        self.assertEqual(contrato.firma_token, data['token'])

    # ──────────────────────────────────────────────────────────
    # TEST 4: Aislamiento Multi-Tenant
    # ──────────────────────────────────────────────────────────

    def test_multi_tenant_isolation(self):
        """
        Un apoderado de la escuela A no debe poder visualizar ni firmar
        contratos de matrícula correspondientes a la escuela B.
        """
        # Crear solicitud en Colegio B
        sol_b = SolicitudAdmision.objects.create(
            colegio=self.colegio_b,
            apoderado=self.apoderado_b,
            ciclo_academico=self.ciclo_b,
            curso_postulado=self.curso_b,
            nombre_estudiante='Ignacia',
            apellido_paterno_estudiante='López',
            apellido_materno_estudiante='Rojas',
            rut_estudiante='26.333.444-5',
            parentesco='MADRE',
            estado='ACEPTADA'
        )

        # Intentar firmar solicitud del Colegio B con el apoderado A
        request = self._build_post_request('/api/apoderado/admisiones/firmar-contrato/', self.apoderado_a, {
            'solicitud_id': sol_b.id_solicitud,
            'rut_firmante': '15.555.555-1',
        })
        
        # El apoderado A no tiene acceso al RBD de B (el resolvedor de RBD fallará o la consulta del service no la encontrará)
        # por lo que debe retornar 404/400 y denegar la firma
        response = firmar_contrato(request)
        self.assertEqual(response.status_code, 400)
        
        # Verificar que no se firmó
        sol_b.refresh_from_db()
        self.assertEqual(sol_b.estado, 'ACEPTADA')
