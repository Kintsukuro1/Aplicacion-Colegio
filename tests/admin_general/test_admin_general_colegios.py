"""
Tests de gestión de colegios a nivel plataforma
"""
from tests.common.test_base import BaseTestCase
from backend.apps.institucion.models import Colegio, Comuna, Region, TipoEstablecimiento, DependenciaAdministrativa
from backend.apps.accounts.models import User


class AdminGeneralColegiosTest(BaseTestCase):
    """Tests de funcionalidad de gestión de colegios"""
    
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        
        # Crear datos necesarios
        cls.region = Region.objects.get_or_create(nombre="Región Metropolitana")[0]
        cls.comuna = Comuna.objects.get_or_create(
            nombre="Santiago",
            region=cls.region
        )[0]
        cls.tipo_establecimiento = TipoEstablecimiento.objects.get_or_create(
            nombre="Particular Subvencionado"
        )[0]
        cls.dependencia = DependenciaAdministrativa.objects.get_or_create(
            nombre="Particular Subvencionado"
        )[0]
    
    def test_admin_general_puede_listar_todos_los_colegios(self):
        """Verificar que el admin general puede ver todos los colegios del sistema"""
        # Crear múltiples colegios
        for i in range(1, 4):
            Colegio.objects.create(
                rbd=95000 + i,
                rut_establecimiento=f"76500{i:03d}-K",
                nombre=f"Colegio Multi {i}",
                comuna=self.comuna,
                tipo_establecimiento=self.tipo_establecimiento,
                dependencia=self.dependencia
            )
        
        colegios = Colegio.objects.all()
        # Contar colegios creados en este test + el colegio base de BaseTestCase
        self.assertGreaterEqual(colegios.count(), 3)
    
    def test_admin_general_puede_ver_usuarios_por_colegio(self):
        """Verificar que puede ver usuarios agrupados por colegio"""
        colegio1 = Colegio.objects.create(
            rbd=95010,
            rut_establecimiento="76500010-K",
            nombre="Colegio A",
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        
        colegio2 = Colegio.objects.create(
            rbd=95011,
            rut_establecimiento="76500011-8",
            nombre="Colegio B",
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        
        # Crear usuarios para cada colegio
        User.objects.create_user(
            email="user1.colegio1@test.cl",
            rut="82000001-5",
            nombre="Usuario",
            apellido_paterno="Uno",
            password="password123",
            rbd_colegio=colegio1.rbd
        )
        
        User.objects.create_user(
            email="user2.colegio2@test.cl",
            rut="82000002-3",
            nombre="Usuario",
            apellido_paterno="Dos",
            password="password123",
            rbd_colegio=colegio2.rbd
        )
        
        usuarios_colegio1 = User.objects.filter(rbd_colegio=colegio1.rbd)
        usuarios_colegio2 = User.objects.filter(rbd_colegio=colegio2.rbd)
        
        self.assertEqual(usuarios_colegio1.count(), 1)
        self.assertEqual(usuarios_colegio2.count(), 1)
    
    def test_admin_general_puede_buscar_colegio_por_rbd(self):
        """Verificar que puede buscar colegios por RBD"""
        colegio = Colegio.objects.create(
            rbd=95020,
            rut_establecimiento="76500020-7",
            nombre="Colegio Búsqueda",
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        
        colegio_encontrado = Colegio.objects.get(rbd=95020)
        self.assertEqual(colegio_encontrado.nombre, "Colegio Búsqueda")
    
    def test_admin_general_puede_filtrar_colegios_por_comuna(self):
        """Verificar que puede filtrar colegios por comuna"""
        comuna2, _ = Comuna.objects.get_or_create(
            nombre="Providencia",
            defaults={"region": self.region}
        )
        
        Colegio.objects.create(
            rbd=95030,
            rut_establecimiento="76500030-4",
            nombre="Colegio Santiago",
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        
        Colegio.objects.create(
            rbd=95031,
            rut_establecimiento="76500031-2",
            nombre="Colegio Providencia",
            comuna=comuna2,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        
        colegios_santiago = Colegio.objects.filter(comuna=self.comuna)
        colegios_providencia = Colegio.objects.filter(comuna=comuna2)
        
        self.assertGreaterEqual(colegios_santiago.count(), 1)
        self.assertEqual(colegios_providencia.count(), 1)
    
    def test_admin_general_puede_contar_colegios_por_region(self):
        """Verificar que puede contar colegios por región"""
        region2, _ = Region.objects.get_or_create(nombre="Región del Biobío")
        comuna_concepcion, _ = Comuna.objects.get_or_create(
            nombre="Concepción",
            region=region2,
            defaults={"region": region2}
        )
        
        colegio_concepcion = Colegio.objects.create(
            rbd=95040,
            rut_establecimiento="76500040-1",
            nombre="Colegio Concepción",
            comuna=comuna_concepcion,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        
        # Contar colegios de la región original y la nueva
        colegios_rm = Colegio.objects.filter(comuna__region=self.region)
        colegios_biobio = Colegio.objects.filter(comuna__region=region2)
        
        # Verificar que el colegio de Concepción está en Biobío
        self.assertEqual(colegio_concepcion.comuna.region, region2)
        self.assertGreaterEqual(colegios_rm.count(), 1)  # Al menos 1 colegio en RM
        self.assertGreaterEqual(colegios_biobio.count(), 1)  # Al menos 1 colegio en Biobío

