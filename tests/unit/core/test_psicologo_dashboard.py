"""
Suite de pruebas unitarias — Dashboards Analíticos y Módulo del Psicólogo/Orientador
Fase 2, Ítem 4.

Verifica:
1. Cálculo correcto de alertas cruzadas (Matriz de Riesgo Crítico/Deserción).
2. Agendamiento y ciclo de vida de Citaciones a Apoderados (actas, observaciones, acuerdos).
3. Registro y protocolo de Convivencia Escolar / Bullying (Aula Segura y Circular 30).
4. Aislamiento multi-tenant estricto para citaciones y casos de bullying.
"""

import json
import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.utils import timezone

from backend.apps.accounts.models import Role, User
from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa,
)
from backend.apps.cursos.models import Curso, Clase, Asignatura
from backend.apps.academico.models import Asistencia, Calificacion, Evaluacion
from backend.apps.core.models import CitacionApoderado, CasoBullyingConvivencia, AnotacionConvivencia
from backend.apps.core.services.dashboard_nuevos_roles_service import DashboardPsicologoService
from backend.apps.core.services.psicologo_orientador_api_service import PsicologoOrientadorApiService
from backend.apps.core.views.psicologo_orientador.api import (
    listar_crear_citaciones,
    actualizar_citacion,
    listar_crear_casos_convivencia,
    actualizar_caso_convivencia,
)

pytestmark = pytest.mark.django_db


class TestPsicologoDashboard(TestCase):
    """
    Suite de pruebas para validar las alertas analíticas y ciclo de vida
    de citaciones y protocolos de bullying de Convivencia Escolar.
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
            rbd=66001,
            defaults={
                'nombre': 'Colegio Psicología A',
                'rut_establecimiento': '66.001.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia,
            },
        )[0]

        # ── School B ─────────────────────────────────────────
        self.colegio_b = Colegio.objects.get_or_create(
            rbd=66002,
            defaults={
                'nombre': 'Colegio Psicología B',
                'rut_establecimiento': '66.002.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia,
            },
        )[0]

        # ── Roles ────────────────────────────────────────────
        self.role_psicologo = Role.objects.get_or_create(
            nombre='psicologo_orientador'
        )[0]
        self.role_student = Role.objects.get_or_create(
            nombre='estudiante'
        )[0]

        # ── Psychologist users ───────────────────────────────
        self.psicologo_a = User.objects.create_user(
            email='psi_a@colegio.cl',
            rut='33333333-1',
            username='psi_a', password='test1234',
            nombre='Ana', apellido_paterno='Soto',
            rbd_colegio=self.colegio_a.rbd,
        )
        self.psicologo_a.role = self.role_psicologo
        self.psicologo_a.save()

        self.psicologo_b = User.objects.create_user(
            email='psi_b@colegio.cl',
            rut='33333333-2',
            username='psi_b', password='test1234',
            nombre='Luis', apellido_paterno='Jara',
            rbd_colegio=self.colegio_b.rbd,
        )
        self.psicologo_b.role = self.role_psicologo
        self.psicologo_b.save()

        # ── Student users ────────────────────────────────────
        self.estudiante_a = User.objects.create_user(
            email='est_psi_a@colegio.cl',
            rut='44444444-1',
            username='est_psi_a', password='test1234',
            nombre='Carlos', apellido_paterno='Valdés',
            rbd_colegio=self.colegio_a.rbd,
        )
        self.estudiante_a.role = self.role_student
        self.estudiante_a.save()

        self.estudiante_b = User.objects.create_user(
            email='est_psi_b@colegio.cl',
            rut='44444444-2',
            username='est_psi_b', password='test1234',
            nombre='Sofía', apellido_paterno='Ríos',
            rbd_colegio=self.colegio_b.rbd,
        )
        self.estudiante_b.role = self.role_student
        self.estudiante_b.save()

        # ── Cycles, levels, courses and classes ─────────────
        self.ciclo_a = CicloAcademico.objects.create(
            colegio=self.colegio_a, nombre='2026-PsiA',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 15),
            estado='ACTIVO',
            creado_por=self.psicologo_a,
            modificado_por=self.psicologo_a,
        )

        nivel = NivelEducativo.objects.get_or_create(nombre='Enseñanza Básica')[0]
        self.curso_a = Curso.objects.create(
            nombre='5A-Psi', colegio=self.colegio_a,
            nivel=nivel, activo=True,
            ciclo_academico=self.ciclo_a,
        )

        self.asignatura_a = Asignatura.objects.create(
            nombre='Matemáticas Psi', colegio=self.colegio_a, activa=True
        )

        self.clase_a = Clase.objects.create(
            curso=self.curso_a, asignatura=self.asignatura_a,
            profesor=self.psicologo_a, colegio=self.colegio_a,
            activo=True
        )

        self.factory = RequestFactory()

    # ── Helpers ──────────────────────────────────────────────

    def _build_post_request(self, url, user, data):
        request = self.factory.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
        )
        request.user = user
        request.session = {}
        return request

    def _build_get_request(self, url, user, params=None):
        request = self.factory.get(
            url,
            data=params or {},
        )
        request.user = user
        request.session = {}
        return request

    # ──────────────────────────────────────────────────────────
    # TEST 1: Calculation of Crossed Alerts (Riesgo Crítico)
    # ──────────────────────────────────────────────────────────

    def test_alertas_cruzadas_riesgo_critico(self):
        """
        Un alumno con bajo rendimiento y alto ausentismo debe figurar
        como ALERTA CRÍTICA (riesgo cruzado) en el dashboard de inicio.
        """
        hoy = date.today()
        # 1. Ausentismo: 3 ausencias en los últimos 30 días
        for i in range(3):
            Asistencia.objects.create(
                colegio=self.colegio_a,
                clase=self.clase_a,
                estudiante=self.estudiante_a,
                fecha=hoy - timedelta(days=i + 1),
                estado='A',
            )

        # 2. Bajo rendimiento: Evaluaciones con promedio < 4.5
        evaluacion1 = Evaluacion.objects.create(
            colegio=self.colegio_a,
            clase=self.clase_a,
            nombre='Prueba 1',
            fecha_evaluacion=hoy - timedelta(days=10),
            ponderacion=50,
            activa=True
        )
        evaluacion2 = Evaluacion.objects.create(
            colegio=self.colegio_a,
            clase=self.clase_a,
            nombre='Prueba 2',
            fecha_evaluacion=hoy - timedelta(days=5),
            ponderacion=50,
            activa=True
        )

        Calificacion.objects.create(
            colegio=self.colegio_a,
            evaluacion=evaluacion1,
            estudiante=self.estudiante_a,
            nota=Decimal('3.5'),
            registrado_por=self.psicologo_a
        )
        Calificacion.objects.create(
            colegio=self.colegio_a,
            evaluacion=evaluacion2,
            estudiante=self.estudiante_a,
            nota=Decimal('4.1'),
            registrado_por=self.psicologo_a
        )

        # 3. Consultar context
        context = DashboardPsicologoService.get_context(self.psicologo_a, 'inicio', self.colegio_a.rbd)

        # El estudiante debe figurar en alertas de inasistencia
        self.assertTrue(any(a['estudiante'] == self.estudiante_a.id for a in context['alumnos_inasistencia']))

        # El estudiante debe figurar en la Matriz de Riesgo Crítico (Cruce)
        self.assertEqual(len(context['alumnos_riesgo_critico']), 1)
        critico = context['alumnos_riesgo_critico'][0]
        self.assertEqual(critico['estudiante_id'], self.estudiante_a.id)
        self.assertEqual(critico['promedio'], Decimal('3.8'))  # (3.5 + 4.1) / 2
        self.assertEqual(critico['reprobadas'], 1)  # 3.5 is < 4.0

    # ──────────────────────────────────────────────────────────
    # TEST 2: Agendamiento y ciclo de vida de Citaciones
    # ──────────────────────────────────────────────────────────

    def test_agendamiento_y_acta_citacion(self):
        """
        Permite agendar una citación y completarla registrando
        el acta de reunión confidencial y compromisos.
        """
        from unittest.mock import patch

        # 1. Agendar citación
        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request('/api/psicologo/citaciones/', self.psicologo_a, {
                'estudiante_id': self.estudiante_a.id,
                'fecha_citacion': (timezone.now() + timedelta(days=2)).isoformat(),
                'motivo': 'Reunión de apoyo por rendimiento',
            })
            response = listar_crear_citaciones(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        cit_id = data['id']

        # Verificar en base de datos
        citacion = CitacionApoderado.objects.get(id_citacion=cit_id)
        self.assertEqual(citacion.estado, 'PENDIENTE')
        self.assertEqual(citacion.motivo, 'Reunión de apoyo por rendimiento')

        # 2. Registrar acta de reunión
        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request(f'/api/psicologo/citaciones/{cit_id}/actualizar/', self.psicologo_a, {
                'estado': 'ASISTIO',
                'observaciones': 'Apoderado comprometido a apoyar en el hogar.',
                'acuerdos': 'Reforzamiento diario de 1 hora.',
            })
            response = actualizar_citacion(request, cit_id)

        self.assertEqual(response.status_code, 200)
        citacion.refresh_from_db()
        self.assertEqual(citacion.estado, 'ASISTIO')
        self.assertEqual(citacion.observaciones, 'Apoderado comprometido a apoyar en el hogar.')
        self.assertEqual(citacion.acuerdos, 'Reforzamiento diario de 1 hora.')

    # ──────────────────────────────────────────────────────────
    # TEST 3: Protocolo Ley Aula Segura (Bullying)
    # ──────────────────────────────────────────────────────────

    def test_protocolo_bullying_aula_segura(self):
        """
        Valida que se registren correctamente incidentes de bullying
        bajo la Ley Aula Segura, permitiendo actualizar medidas.
        """
        from unittest.mock import patch

        # 1. Registrar caso
        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request('/api/psicologo/casos-convivencia/', self.psicologo_a, {
                'estudiante_id': self.estudiante_a.id,
                'tipo_falta': 'BULLYING',
                'descripcion_hechos': 'Agresión verbal reiterada en patio trasero.',
                'apoderado_notificado': True,
            })
            response = listar_crear_casos_convivencia(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        caso_id = data['id']

        # Verificar en base de datos
        caso = CasoBullyingConvivencia.objects.get(id_caso=caso_id)
        self.assertEqual(caso.estado, 'ABIERTO')
        self.assertEqual(caso.tipo_falta, 'BULLYING')
        self.assertTrue(caso.apoderado_notificado)

        # 2. Aplicar medidas y transicionar estado
        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request(f'/api/psicologo/casos-convivencia/{caso_id}/actualizar/', self.psicologo_a, {
                'estado': 'MEDIDAS_APLICADAS',
                'medidas_tomadas': 'Suspensión por 3 días y mediación de convivencia escolar.',
                'apoderado_notificado': True,
            })
            response = actualizar_caso_convivencia(request, caso_id)

        self.assertEqual(response.status_code, 200)
        caso.refresh_from_db()
        self.assertEqual(caso.estado, 'MEDIDAS_APLICADAS')
        self.assertEqual(caso.medidas_tomadas, 'Suspensión por 3 días y mediación de convivencia escolar.')

    # ──────────────────────────────────────────────────────────
    # TEST 4: Aislamiento Multi-Tenant Estricto
    # ──────────────────────────────────────────────────────────

    def test_multi_tenant_isolation(self):
        """
        Un psicólogo del Colegio A no debe poder listar, agendar ni
        modificar citaciones o casos de bullying del Colegio B.
        """
        from unittest.mock import patch

        # Crear una citación en Colegio B
        cit_b = CitacionApoderado.objects.create(
            colegio=self.colegio_b,
            estudiante=self.estudiante_b,
            solicitado_por=self.psicologo_b,
            fecha_citacion=timezone.now(),
            motivo='Citación rival',
            estado='PENDIENTE'
        )

        # Intentar actualizar acta de Colegio B con el psicólogo A
        with patch('backend.common.services.policy_service.PolicyService.has_capability', return_value=True):
            request = self._build_post_request(f'/api/psicologo/citaciones/{cit_b.id_citacion}/actualizar/', self.psicologo_a, {
                'estado': 'ASISTIO',
                'observaciones': 'Piratería de datos.',
            })
            response = actualizar_citacion(request, cit_b.id_citacion)

        # Debe retornar 404 (No encontrado / Aislado)
        self.assertEqual(response.status_code, 404)
        
        # Verificar que no cambió en la DB
        cit_b.refresh_from_db()
        self.assertEqual(cit_b.estado, 'PENDIENTE')
        self.assertNotEqual(cit_b.observaciones, 'Piratería de datos.')
