"""Tests funcionales del setup wizard alineados al esquema actual."""

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from backend.apps.accounts.models import Role
from backend.apps.cursos.models import Curso
from backend.apps.institucion.models import (
    CicloAcademico,
    Colegio,
    Comuna,
    DependenciaAdministrativa,
    NivelEducativo,
    Region,
    TipoEstablecimiento,
)
from backend.common.constants import CICLO_ESTADO_ACTIVO

User = get_user_model()


@pytest.mark.django_db
class TestSetupWizardValidation:
    @pytest.fixture
    def colegio(self):
        region = Region.objects.create(nombre='Region Setup')
        comuna = Comuna.objects.create(nombre='Comuna Setup', region=region)
        tipo = TipoEstablecimiento.objects.create(nombre='Tipo Setup')
        dependencia = DependenciaAdministrativa.objects.create(nombre='Dependencia Setup')
        return Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='76000000-1',
            nombre='Colegio Setup Test',
            direccion='Direccion 123',
            comuna=comuna,
            tipo_establecimiento=tipo,
            dependencia=dependencia,
        )

    @pytest.fixture
    def admin_user(self, colegio):
        rol_admin, _ = Role.objects.get_or_create(nombre='admin')
        return User.objects.create_user(
            email='admin.setup@test.cl',
            password='AdminStrongPass123!',
            nombre='Admin',
            apellido_paterno='Setup',
            rut='11111111-1',
            rbd_colegio=colegio.rbd,
            role=rol_admin,
        )

    @pytest.fixture
    def authenticated_client(self, admin_user):
        client = Client()
        client.force_login(admin_user)
        return client

    @pytest.fixture
    def nivel_educativo(self):
        return NivelEducativo.objects.create(nombre='Basica')

    def test_get_wizard_disponible_para_admin(self, authenticated_client):
        response = authenticated_client.get(reverse('setup_wizard'))
        assert response.status_code == 200

    def test_crea_ciclo_academico_con_datos_validos(self, authenticated_client, colegio):
        response = authenticated_client.post(
            reverse('setup_wizard'),
            {
                'nombre': 'Ciclo 2026',
                'anio': 2026,
                'fecha_inicio': '2026-03-01',
                'fecha_fin': '2026-12-15',
            },
        )

        assert response.status_code == 302
        assert CicloAcademico.objects.filter(
            colegio=colegio,
            nombre='Ciclo 2026',
            estado=CICLO_ESTADO_ACTIVO,
        ).exists()

    def test_rechaza_ciclo_con_fechas_invalidas(self, authenticated_client, colegio):
        response = authenticated_client.post(
            reverse('setup_wizard'),
            {
                'nombre': 'Ciclo Invalido',
                'anio': 2026,
                'fecha_inicio': '2026-12-01',
                'fecha_fin': '2026-03-01',
            },
            follow=True,
        )

        assert response.status_code == 200
        assert not CicloAcademico.objects.filter(
            colegio=colegio,
            nombre='Ciclo Invalido',
        ).exists()

    def test_crea_curso_cuando_existe_ciclo_activo(
        self,
        authenticated_client,
        admin_user,
        colegio,
        nivel_educativo,
    ):
        ciclo = CicloAcademico.objects.create(
            colegio=colegio,
            nombre='Ciclo Activo',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=220),
            estado=CICLO_ESTADO_ACTIVO,
            creado_por=admin_user,
            modificado_por=admin_user,
        )

        response = authenticated_client.post(
            reverse('setup_wizard'),
            {
                'nivel': nivel_educativo.id_nivel,
                'grado': 1,
                'letra': 'A',
                'cantidad': 1,
            },
        )

        assert response.status_code == 302
        assert Curso.objects.filter(
            colegio=colegio,
            ciclo_academico=ciclo,
            nombre='1° Basica A',
            activo=True,
        ).exists()
