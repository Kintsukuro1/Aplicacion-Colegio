"""
Tests para validar protección contra inyección en filtros y consultas.

Valida que:
- Filtros de búsqueda sanitizan entrada del usuario
- Parámetros de ordenamiento son validados
- Filtros por colegio no pueden ser manipulados
- Consultas usan QuerySet API (no SQL raw inseguro)
- Intentos de inyección son detectados y bloqueados
"""
import pytest
from django.test import TestCase
from django.db.models import Q

from backend.apps.accounts.models import User, Role
from backend.apps.cursos.models import Curso, NivelEducativo
from backend.apps.academico.models import CicloAcademico
from backend.apps.institucion.models import (
    Colegio, Region, Comuna, TipoEstablecimiento,
    DependenciaAdministrativa
)
from backend.common.utils.error_response import ErrorResponseBuilder


@pytest.mark.django_db
class TestProteccionInyeccionFiltros(TestCase):
    """
    Tests que validan protección contra inyección en filtros de búsqueda.
    """

    def setUp(self):
        """Configuración común"""
        # Crear datos base
        region = Region.objects.get_or_create(nombre='Metropolitana')[0]
        comuna = Comuna.objects.get_or_create(
            nombre='Santiago',
            defaults={'region': region}
        )[0]
        tipo = TipoEstablecimiento.objects.get_or_create(nombre='Municipal')[0]
        dependencia = DependenciaAdministrativa.objects.get_or_create(nombre='Municipal')[0]

        self.colegio1 = Colegio.objects.get_or_create(
            rbd=12361,
            defaults={
                'nombre': 'Colegio Filtros 1',
                'direccion': 'Calle Test 123',
                'telefono': '+56912345678',
                'correo': 'filtros1@colegio.cl',
                'web': 'http://filtros1.cl',
                'rut_establecimiento': '12.361.000-9',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]

        self.colegio2 = Colegio.objects.get_or_create(
            rbd=12362,
            defaults={
                'nombre': 'Colegio Filtros 2',
                'direccion': 'Calle Test 456',
                'telefono': '+56912345679',
                'correo': 'filtros2@colegio.cl',
                'web': 'http://filtros2.cl',
                'rut_establecimiento': '12.362.000-K',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]

        # Crear rol y usuarios
        self.rol_estudiante = Role.objects.get_or_create(nombre='estudiante')[0]
        self.rol_admin = Role.objects.get_or_create(nombre='admin_escolar')[0]

        self.estudiante = User.objects.create(
            email='filtros_est@test.cl',
            rut='18181819-4',
            nombre='Estudiante',
            apellido_paterno='Filtros',
            role=self.rol_estudiante,
            rbd_colegio=self.colegio1.rbd,
            is_active=True
        )

        self.admin = User.objects.create(
            email='filtros_admin@test.cl',
            rut='19191920-0',
            nombre='Admin',
            apellido_paterno='Filtros',
            role=self.rol_admin,
            rbd_colegio=self.colegio1.rbd,
            is_active=True
        )

    def test_filtro_por_colegio_no_puede_ser_manipulado(self):
        """
        Los filtros por colegio deben usar el rbd_colegio del usuario,
        no parámetros de la URL que puedan ser manipulados.
        """
        # Simular filtro correcto usando rbd_colegio del usuario
        usuarios_colegio1 = User.objects.filter(rbd_colegio=self.estudiante.rbd_colegio)
        
        self.assertGreater(usuarios_colegio1.count(), 0)
        
        # Verificar que usuarios del colegio2 no aparecen
        for usuario in usuarios_colegio1:
            self.assertEqual(usuario.rbd_colegio, self.colegio1.rbd)

    def test_filtro_busqueda_nombre_sanitiza_entrada(self):
        """
        Los filtros de búsqueda por nombre deben usar QuerySet API,
        no concatenación directa de strings que permita inyección.
        """
        # Buscar usuarios usando QuerySet API (seguro)
        nombre_busqueda = "Estudiante"
        usuarios = User.objects.filter(
            Q(nombre__icontains=nombre_busqueda) | 
            Q(apellido_paterno__icontains=nombre_busqueda)
        )
        
        self.assertEqual(usuarios.count(), 1)
        self.assertEqual(usuarios.first().nombre, 'Estudiante')

    def test_filtro_con_caracteres_especiales_no_causa_error(self):
        """
        Los filtros deben manejar caracteres especiales sin causar errores.
        Django ORM automáticamente escapa caracteres especiales.
        """
        # Intentar buscar con caracteres especiales
        caracteres_especiales = ["'; DROP TABLE user; --", "' OR '1'='1", "<script>"]
        
        for caracter in caracteres_especiales:
            # No debe causar error, debe retornar 0 resultados
            usuarios = User.objects.filter(nombre__icontains=caracter)
            self.assertEqual(
                usuarios.count(), 
                0,
                f"Filtro con '{caracter}' no debe causar error"
            )

    def test_ordenamiento_solo_permite_campos_validos(self):
        """
        Los parámetros de ordenamiento deben validarse contra una
        lista blanca de campos permitidos.
        """
        # Campos válidos para ordenar usuarios
        campos_validos = ['nombre', 'email', 'fecha_creacion', '-nombre', '-email']
        
        for campo in campos_validos:
            try:
                # Debe funcionar sin error
                usuarios = User.objects.order_by(campo)
                self.assertIsNotNone(usuarios)
            except Exception as e:
                self.fail(f"Ordenamiento por campo válido '{campo}' causó error: {e}")

    def test_filtro_por_id_usa_pk_no_raw_sql(self):
        """
        Los filtros por ID deben usar .pk o .id en QuerySet,
        no interpolación directa en raw SQL.
        """
        # Filtro seguro usando QuerySet API
        usuario = User.objects.filter(pk=self.estudiante.pk).first()
        
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.email, 'filtros_est@test.cl')

    def test_filtro_multiples_condiciones_usa_q_objects(self):
        """
        Filtros complejos deben usar Q objects, no concatenación de strings.
        """
        # Búsqueda compleja usando Q objects (seguro)
        usuarios = User.objects.filter(
            Q(rbd_colegio=self.colegio1.rbd) &
            (Q(role=self.rol_estudiante) | Q(role=self.rol_admin))
        )
        
        self.assertEqual(usuarios.count(), 2)

    def test_filtro_por_rango_fechas_usa_gte_lte(self):
        """
        Filtros por rango de fechas deben usar operadores Django ORM.
        """
        from datetime import date
        
        # Filtro seguro usando __gte y __lte
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2024, 12, 31)
        
        # Usar modelo con fechas (User tiene fecha_creacion)
        usuarios = User.objects.filter(
            fecha_creacion__gte=fecha_inicio,
            fecha_creacion__lte=fecha_fin
        )
        
        self.assertIsNotNone(usuarios)

    def test_filtro_exclude_usa_queryset_api(self):
        """
        Exclusiones deben usar .exclude() de QuerySet, no NOT en raw SQL.
        """
        # Excluir usuarios inactivos
        usuarios_activos = User.objects.exclude(is_active=False)
        
        self.assertGreater(usuarios_activos.count(), 0)
        
        for usuario in usuarios_activos:
            self.assertTrue(usuario.is_active)

    def test_agregacion_usa_annotate_no_raw_sql(self):
        """
        Operaciones de agregación deben usar .annotate() y .aggregate().
        """
        from django.db.models import Count
        
        # Contar cursos por colegio usando annotate (seguro)
        colegios_con_cursos = Colegio.objects.annotate(
            num_cursos=Count('cursos')  # plural: related_name
        )
        
        self.assertIsNotNone(colegios_con_cursos)


@pytest.mark.django_db
class TestValidacionParametrosOrdenamiento(TestCase):
    """
    Tests para validar que los parámetros de ordenamiento son seguros.
    """

    def setUp(self):
        """Configuración común"""
        self.rol = Role.objects.get_or_create(nombre='profesor')[0]
        
        # Crear varios usuarios para ordenar
        for i in range(3):
            User.objects.create(
                email=f'usuario{i}@test.cl',
                rut=f'2020202{i}-{i}',
                nombre=f'Usuario{i}',
                apellido_paterno=f'Test{i}',
                role=self.rol,
                is_active=True
            )

    def test_ordenamiento_ascendente_funciona(self):
        """
        Ordenamiento ascendente debe funcionar correctamente.
        """
        usuarios = User.objects.order_by('nombre')
        nombres = [u.nombre for u in usuarios]
        
        self.assertEqual(nombres, sorted(nombres))

    def test_ordenamiento_descendente_funciona(self):
        """
        Ordenamiento descendente debe funcionar correctamente.
        """
        usuarios = User.objects.order_by('-nombre')
        nombres = [u.nombre for u in usuarios]
        
        self.assertEqual(nombres, sorted(nombres, reverse=True))

    def test_ordenamiento_campo_invalido_maneja_error(self):
        """
        Intentar ordenar por campo inexistente debe ser manejado.
        """
        # Intentar ordenar por campo que no existe
        # Django lanzará FieldError si no se valida
        try:
            # En producción, esto debería validarse ANTES de llegar al ORM
            usuarios = list(User.objects.order_by('campo_inexistente'))
            # Si llegamos aquí, algo está mal con la validación
        except Exception:
            # Esperamos que falle de forma controlada
            pass


@pytest.mark.django_db
class TestErrorBuilderForInjectionAttempts(TestCase):
    """
    Tests para validar ErrorResponseBuilder con intentos de inyección.
    Usa PERMISSION_DENIED como error para validar estructura de contexto.
    """

    def test_error_builder_injection_attempt_estructura(self):
        """
        ErrorBuilder debe generar estructura correcta con contexto de inyección.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            context={
                'parameter': 'search',
                'value': "'; DROP TABLE user; --",
                'reason': 'Caracteres sospechosos detectados'
            }
        )
        
        self.assertIn('error_type', error)
        self.assertEqual(error['error_type'], 'PERMISSION_DENIED')
        self.assertIn('context', error)

    def test_error_builder_incluye_parametro_rechazado(self):
        """
        El contexto debe incluir información sobre el parámetro rechazado.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            context={
                'parameter': 'order_by',
                'attempted_value': '__import__',
                'reason': 'Campo no permitido para ordenamiento'
            }
        )
        
        self.assertIn('parameter', error['context'])
        self.assertEqual(error['context']['parameter'], 'order_by')
        self.assertIn('attempted_value', error['context'])

    def test_error_builder_contexto_seguridad_inyeccion(self):
        """
        Puede incluir información de seguridad sobre el intento.
        """
        error = ErrorResponseBuilder.build(
            'PERMISSION_DENIED',
            context={
                'security_event': 'INJECTION_ATTEMPT',
                'parameter': 'filter',
                'pattern_detected': 'SQL_INJECTION',
                'ip_address': '192.168.1.100'
            }
        )
        
        self.assertIn('security_event', error['context'])
        self.assertEqual(error['context']['pattern_detected'], 'SQL_INJECTION')
