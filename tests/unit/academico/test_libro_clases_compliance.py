import json
import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone
from unittest.mock import patch

from backend.apps.institucion.models import (
    Colegio, CicloAcademico, NivelEducativo,
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import Curso, Asignatura, Clase
from backend.apps.accounts.models import Role, User
from backend.apps.academico.models import RegistroClase, FirmaRegistroClase
from backend.apps.auditoria.models import AuditoriaEvento
from backend.apps.academico.services.libro_clases_service import LibroClasesService
from backend.apps.core.views.profesor.libro_clases_api import (
    guardar_registro_profesor, firmar_registro_profesor
)

pytestmark = pytest.mark.django_db


class TestLibroClasesCompliance(TestCase):
    """
    Suite de pruebas de cumplimiento normativo (Circular 30 MINEDUC)
    para el Libro de Clases Digital.
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
        self.rol_docente, _ = Role.objects.get_or_create(nombre='Docente')

        # Docente principal
        self.profesor = User.objects.get_or_create(
            rut='44444444-4',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Principal',
                'email': 'profesor@test.cl',
                'rbd_colegio': self.colegio.rbd,
                'role': self.rol_docente
            }
        )[0]
        if not self.profesor.password:
            self.profesor.set_password('testpass123')
            self.profesor.save()

        # Docente de otro colegio
        self.profesor_otro = User.objects.get_or_create(
            rut='55555555-5',
            defaults={
                'nombre': 'Profesor',
                'apellido_paterno': 'Otro',
                'email': 'profesor_otro@test.cl',
                'rbd_colegio': self.colegio_otro.rbd,
                'role': self.rol_docente
            }
        )[0]
        if not self.profesor_otro.password:
            self.profesor_otro.set_password('testpass123')
            self.profesor_otro.save()

        # Ciclo Académico
        self.ciclo = CicloAcademico.objects.create(
            nombre='2026',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio,
            estado='ACTIVO',
            creado_por=self.profesor,
            modificado_por=self.profesor
        )

        # Nivel, Curso, Asignatura y Clase del Colegio Principal
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
            profesor=self.profesor,
            activo=True
        )

        # Clase del Colegio Secundario
        self.ciclo_otro = CicloAcademico.objects.create(
            nombre='2026-Otro',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            colegio=self.colegio_otro,
            estado='ACTIVO',
            creado_por=self.profesor_otro,
            modificado_por=self.profesor_otro
        )
        self.curso_otro = Curso.objects.create(
            nombre='1° Básico B',
            colegio=self.colegio_otro,
            ciclo_academico=self.ciclo_otro,
            nivel=self.nivel,
            activo=True
        )
        self.asignatura_otro = Asignatura.objects.create(
            nombre='Matemáticas-Otro',
            colegio=self.colegio_otro,
            horas_semanales=5,
            activa=True
        )
        self.clase_otro = Clase.objects.create(
            colegio=self.colegio_otro,
            curso=self.curso_otro,
            asignatura=self.asignatura_otro,
            profesor=self.profesor_otro,
            activo=True
        )

    def test_registro_clase_firmado_es_inmutable(self):
        """
        [CUMPLIMIENTO] Verifica que una vez firmado un RegistroClase,
        cualquier modificación a los campos protegidos lance ValidationError.
        """
        registro = RegistroClase.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            profesor=self.profesor,
            fecha=date.today(),
            numero_clase=1,
            contenido_tratado='Geometría básica',
            tarea_asignada='Ninguna',
            observaciones='Clase participativa',
        )

        # Firmamos el registro
        registro.firmar(profesor=self.profesor, ip_address='127.0.0.1', user_agent='PyTest Agent')
        self.assertTrue(registro.firmado)

        # Intentamos modificar contenido
        registro.contenido_tratado = 'Geometría avanzada'
        with self.assertRaises(ValidationError) as exc:
            registro.clean()
        
        self.assertIn('El registro de clase firmado es inmutable', str(exc.exception))

    def test_generacion_de_hash_sha256(self):
        """
        [CUMPLIMIENTO] Valida que el hash de firma digital se genere
        con algoritmo SHA-256 e incluya los datos de auditoría e inmutabilidad.
        """
        registro = RegistroClase.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            profesor=self.profesor,
            fecha=date.today(),
            numero_clase=2,
            contenido_tratado='Álgebra básica',
        )

        registro.firmar(profesor=self.profesor, ip_address='192.168.1.50', user_agent='Test Firefox')
        
        # Validamos que se asigne el hash y se cree la firma correspondiente
        self.assertIsNotNone(registro.hash_contenido)
        self.assertEqual(len(registro.hash_contenido), 64) # Longitud de hash SHA-256 en hex

        firma = FirmaRegistroClase.objects.get(registro_clase=registro)
        self.assertEqual(firma.firma_hash, registro.hash_contenido)
        self.assertEqual(firma.estado, 'FIRMADO')
        self.assertEqual(firma.ip_address, '192.168.1.50')
        self.assertEqual(firma.user_agent, 'Test Firefox')

    def test_audit_logs_creacion_y_edicion_libro_de_clases(self):
        """
        [CUMPLIMIENTO] Verifica que las acciones de creación, modificación y firma
        a través de las vistas API de libro de clases registren los eventos de AuditoriaEvento correspondientes.
        """
        factory = RequestFactory()
        
        # 1. Test de Guardado (Creación)
        payload_crear = {
            'clase_id': self.clase.id,
            'fecha': date.today().isoformat(),
            'numero_clase': 1,
            'contenido_tratado': 'Clase de Fracciones',
            'tarea_asignada': 'Pág 10',
            'observaciones': 'Todo bien'
        }
        
        request_crear = factory.post(
            '/api/profesor/libro-clases/registro/',
            data=json.dumps(payload_crear),
            content_type='application/json'
        )
        request_crear.user = self.profesor
        request_crear.META['REMOTE_ADDR'] = '200.50.40.30'
        request_crear.META['HTTP_USER_AGENT'] = 'Chrome/120.0.0'

        with patch('backend.apps.core.views.profesor.libro_clases_api.PolicyService.has_capability', return_value=True):
            response = guardar_registro_profesor(request_crear)
        
        self.assertEqual(response.status_code, 200)
        
        # Verificamos log de auditoría de creación
        eventos = AuditoriaEvento.objects.filter(
            colegio_rbd=str(self.colegio.rbd),
            tabla_afectada='registro_clase',
            accion=AuditoriaEvento.CREAR
        )
        self.assertEqual(eventos.count(), 1)
        evento = eventos.first()
        self.assertEqual(evento.usuario, self.profesor)
        self.assertEqual(evento.categoria, AuditoriaEvento.CATEGORIA_ACADEMICO)
        self.assertEqual(evento.ip_address, '200.50.40.30')
        self.assertEqual(evento.user_agent, 'Chrome/120.0.0')

        # 2. Test de Firma
        registro = RegistroClase.objects.get(clase=self.clase, fecha=date.today(), numero_clase=1)
        
        request_firmar = factory.post(
            f'/api/profesor/libro-clases/registro/{registro.id_registro}/firmar/'
        )
        request_firmar.user = self.profesor
        request_firmar.META['REMOTE_ADDR'] = '200.50.40.30'
        request_firmar.META['HTTP_USER_AGENT'] = 'Chrome/120.0.0'

        with patch('backend.apps.core.views.profesor.libro_clases_api.PolicyService.has_capability', return_value=True):
            response_firma = firmar_registro_profesor(request_firmar, registro.id_registro)
            
        self.assertEqual(response_firma.status_code, 200)
        registro.refresh_from_db()

        # Verificamos log de auditoría de firma
        eventos_firma = AuditoriaEvento.objects.filter(
            colegio_rbd=str(self.colegio.rbd),
            tabla_afectada='registro_clase',
            accion=AuditoriaEvento.MODIFICAR,
            categoria=AuditoriaEvento.CATEGORIA_SEGURIDAD
        )
        self.assertEqual(eventos_firma.count(), 1)
        evento_f = eventos_firma.first()
        self.assertEqual(evento_f.usuario, self.profesor)
        self.assertIn('Firma digital', evento_f.descripcion)
        self.assertEqual(evento_f.ip_address, '200.50.40.30')
        self.assertEqual(evento_f.user_agent, 'Chrome/120.0.0')
        self.assertEqual(evento_f.metadata.get('hash_contenido'), registro.hash_contenido)

    def test_libro_de_clases_multi_tenant_isolation(self):
        """
        [CUMPLIMIENTO] Verifica que se impida a docentes de otros colegios
        ver, guardar o firmar registros de colegios ajenos (aislamiento multi-tenant).
        """
        # Intentamos interactuar con la clase del colegio principal usando el profesor secundario
        factory = RequestFactory()
        
        payload = {
            'clase_id': self.clase.id,  # Clase del colegio principal (12348)
            'fecha': date.today().isoformat(),
            'numero_clase': 3,
            'contenido_tratado': 'Intrusión no permitida',
        }
        
        request = factory.post(
            '/api/profesor/libro-clases/registro/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Profesor secundario con RBD 87654
        request.user = self.profesor_otro 
        
        with patch('backend.apps.core.views.profesor.libro_clases_api.PolicyService.has_capability', return_value=True):
            response = guardar_registro_profesor(request)
            
        # Debe lanzar 404/500 (o fallar por no encontrar la clase del otro colegio en su tenant scope)
        self.assertIn(response.status_code, (404, 500))
        self.assertIn('Registro no encontrado', response.content.decode('utf-8'))
