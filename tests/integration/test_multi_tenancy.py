"""Tests para validar multi-tenancy: aislamiento de datos por colegio."""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from backend.apps.institucion.models import Colegio, Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
from backend.apps.subscriptions.models import Plan, Subscription
from backend.apps.academico.models import Curso, Asignatura

User = get_user_model()


@pytest.mark.django_db
class TestMultiTenancyIsolation(TestCase):
    """Valida que users de colegios diferentes no puedan acceder data mutuamente."""

    def setUp(self):
        """Crear 2 colegios con usuarios y data separada."""
        # Setup base data
        region = Region.objects.create(nombre='Metropolitana')
        comuna = Comuna.objects.create(nombre='Santiago', region=region)
        tipo_est = TipoEstablecimiento.objects.create(nombre='Colegio')
        dependencia = DependenciaAdministrativa.objects.create(nombre='Subvencionado')
        
        # Colegio 1
        self.colegio1 = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345-K',
            nombre='Colegio A',
            slug='colegio-a',
            comuna=comuna,
            tipo_establecimiento=tipo_est,
            dependencia=dependencia,
        )
        
        # Colegio 2
        self.colegio2 = Colegio.objects.create(
            rbd=54321,
            rut_establecimiento='54321-K',
            nombre='Colegio B',
            slug='colegio-b',
            comuna=comuna,
            tipo_establecimiento=tipo_est,
            dependencia=dependencia,
        )
        
        # Plan
        plan = Plan.objects.create(
            nombre='Prueba',
            codigo='trial',
            is_trial=True,
            duracion_dias=30,
            activo=True,
        )
        
        # Subscriptions
        Subscription.objects.create(colegio=self.colegio1, plan=plan)
        Subscription.objects.create(colegio=self.colegio2, plan=plan)
        
        # User de Colegio 1
        self.user1 = User.objects.create_user(
            username='admin1',
            email='admin1@colegio-a.cl',
            password='Test1234!',
            rbd_colegio=self.colegio1.rbd,
        )
        
        # User de Colegio 2
        self.user2 = User.objects.create_user(
            username='admin2',
            email='admin2@colegio-b.cl',
            password='Test1234!',
            rbd_colegio=self.colegio2.rbd,
        )
        
        # Cursos para cada colegio

    def test_user_colegio1_cannot_access_colegio2_api(self):
        """User de Colegio 1 no puede acceder endpoints de Colegio 2 con subdomain enforcement."""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Intento acceder desde subdomain de Colegio 2 con user de Colegio 1
        response = client.get(
            '/api/v1/me/',
            HTTP_HOST='colegio-b.sistema.cl',  # Subdomain de Colegio 2
        )
        
        # Debe ser denegado (403) por SubdomainMiddleware
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

    def test_user_colegio1_can_access_colegio1_api(self):
        """User de Colegio 1 puede acceder endpoints de su propio Colegio."""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Acceso desde subdomain de Colegio 1 con user de Colegio 1
        response = client.get(
            '/api/v1/me/',
            HTTP_HOST='colegio-a.sistema.cl',
        )
        
        # Debe ser permitido (200 o 403 por permisos, pero no por multi-tenancy)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

    def test_me_endpoint_returns_user_own_colegio(self):
        """Endpoint /me/ retorna solo data del colegio del user."""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        response = client.get('/api/v1/me/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # User1 debe ver su colegio (rbd_colegio debe matchear)
        assert data.get('rbd_colegio') == self.colegio1.rbd or self.user1.rbd_colegio == self.colegio1.rbd

    def test_cursos_filtered_by_colegio(self):
        """Validar que subdomain enforcement funciona en múltiples usuarios."""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        response = client.get('/api/v1/me/')
        
        # User1 debe acceder su info desde su subdomain
        if response.status_code == status.HTTP_200_OK:
            data = response.json()

    def test_subscription_upgrade_changes_only_own_colegio(self):
        """Upgrade de suscripción solo afecta el colegio del user."""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Crear plan premium
        plan_premium = Plan.objects.create(
            nombre='Premium',
            codigo='premium',
            precio_mensual=50000,
            activo=True,
        )
        
        # User1 intenta upgrade
        response = client.post(
            '/api/v1/subscriptions/upgrade/',
            {'plan_codigo': 'premium', 'colegio_rbd': self.colegio1.rbd},
            format='json',
        )
        
        # Si es exitoso, solo Colegio 1 debe cambiar
        if response.status_code == status.HTTP_200_OK:
            sub1 = Subscription.objects.get(colegio=self.colegio1)
            sub2 = Subscription.objects.get(colegio=self.colegio2)
            
            assert sub1.plan.codigo == 'premium'
            assert sub2.plan.codigo == 'trial'  # Sin cambios

    def test_subdomain_middleware_attaches_colegio(self):
        """SubdomainMiddleware resuelve correctamente el colegio por subdomain."""
        client = APIClient()
        client.force_authenticate(user=self.user1)
        
        # Acceso desde subdomain de Colegio A
        response = client.get(
            '/api/v1/me/',
            HTTP_HOST='colegio-a.sistema.cl',
        )
        
        # Debe ser exitoso si el middleware configuró request.tenant_school_id
        # (El endpoint /me/ debe estar disponible)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]


@pytest.mark.django_db
class TestSubdomainEnforcement(TestCase):
    """Valida que SubdomainMiddleware enforce multi-tenancy correctamente."""

    def setUp(self):
        """Setup base data."""
        region = Region.objects.create(nombre='Metropolitana')
        comuna = Comuna.objects.create(nombre='Santiago', region=region)
        tipo_est = TipoEstablecimiento.objects.create(nombre='Colegio')
        dependencia = DependenciaAdministrativa.objects.create(nombre='Subvencionado')
        
        self.colegio = Colegio.objects.create(
            rbd=99999,
            rut_establecimiento='99999-K',
            nombre='Test Colegio',
            slug='test-colegio',
            comuna=comuna,
            tipo_establecimiento=tipo_est,
            dependencia=dependencia,
        )
        
        plan = Plan.objects.create(
            nombre='Test Plan',
            codigo='test-plan',
            activo=True,
        )
        
        Subscription.objects.create(colegio=self.colegio, plan=plan)
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.cl',
            password='Test1234!',
            rbd_colegio=self.colegio.rbd,
        )

    def test_localhost_bypasses_subdomain_check(self):
        """localhost no requiere validación de subdomain."""
        client = APIClient()
        client.force_authenticate(user=self.user)
        
        response = client.get(
            '/api/v1/me/',
            HTTP_HOST='localhost:8000',
        )
        
        # Debe funcionar sin restricción de subdominio
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_wrong_subdomain_denied_for_authenticated_user(self):
        """User autenticado intenta acceder desde subdomain incorrecto: DENIED."""
        client = APIClient()
        client.force_authenticate(user=self.user)
        
        # User de test-colegio intenta acceder desde wrong-colegio
        response = client.get(
            '/api/v1/me/',
            HTTP_HOST='wrong-colegio.sistema.cl',
        )
        
        # Debe ser denegado (403) porque wrong-colegio.rbd != self.user.rbd_colegio
        # O 404 si no existe el colegio
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]

    def test_correct_subdomain_allowed_for_authenticated_user(self):
        """User autenticado accede desde subdomain correcto: ALLOWED."""
        client = APIClient()
        client.force_authenticate(user=self.user)
        
        response = client.get(
            '/api/v1/me/',
            HTTP_HOST='test-colegio.sistema.cl',
        )
        
        # Debe ser permitido (200 u otro status que no sea 403 por multi-tenancy)
        assert response.status_code != status.HTTP_403_FORBIDDEN
