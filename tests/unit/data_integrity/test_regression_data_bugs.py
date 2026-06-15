"""
Tests de regresión para bugs de integridad de datos.

Este módulo contiene tests que reproducen los 5 tipos de bugs detectados
por audit_data_integrity.py y valida que:
1. Las validaciones defensivas los previenen
2. Los comandos fix y audit funcionan correctamente
3. No pueden volver a ocurrir

Los 5 tipos de bugs son:
1. Matrículas activas con cursos/ciclos inválidos
2. Cursos activos con ciclos no ACTIVO
3. Clases activas con curso/profesor inválidos
4. Users con rbd_colegio huérfano
5. Perfiles estudiante con ciclos inválidos
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date
from io import StringIO
import json
import re
import sys


class UTF8StringIO(StringIO):
    """StringIO wrapper que maneja caracteres UTF-8 correctamente"""
    def write(self, s):
        # Convertir a string si no lo es, manejando caracteres Unicode
        if isinstance(s, bytes):
            s = s.decode('utf-8', errors='replace')
        elif not isinstance(s, str):
            s = str(s)
        return super().write(s)

from backend.apps.institucion.models import (
    Colegio, CicloAcademico, Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.accounts.models import Role, PerfilEstudiante
from backend.apps.cursos.models import Curso, NivelEducativo, Clase
from backend.apps.matriculas.models import Matricula
from backend.apps.academico.models import Asignatura
from backend.apps.core.management.commands.audit_data_integrity import Command as AuditCommand
from backend.apps.core.management.commands.fix_data_integrity import Command as FixCommand

User = get_user_model()


def parse_audit_output(output_str):
    """Helper para extraer JSON del output del comando audit"""
    # El JSON puede estar pegado al final de una línea de texto
    # Buscar la posición donde comienza el JSON (primer { seguido de "timestamp")
    
    # Buscar el patrón {"timestamp" o ...\n{"timestamp"
    import re
    pattern = r'\{[\s\n]*"timestamp"'
    match = re.search(pattern, output_str)
    
    if not match:
        return None
    
    # Extraer desde el { hasta el final
    json_start = match.start()
    json_str = output_str[json_start:]
    
    # Encontrar dónde termina el JSON (balance de llaves)
    brace_count = 0
    json_end = 0
    
    for i, char in enumerate(json_str):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break
    
    if json_end == 0:
        return None
    
    try:
        return json.loads(json_str[:json_end])
    except json.JSONDecodeError:
        return None


class TestRegressionMatriculasInvalidCiclo(TestCase):
    """
    Test de regresión: Bug #1 - Matrículas activas con cursos/ciclos inválidos
    
    Escenario: Una matrícula está marcada como ACTIVA pero:
    - Su curso está inactivo, O
    - Su ciclo está cerrado/finalizado, O
    - El curso pertenece a un ciclo diferente al de la matrícula
    
    Este bug causaba que get_estado_cuenta_data() mostrara matrículas de ciclos cerrados
    y que los dashboards contaran estudiantes de años anteriores.
    """

    def setUp(self):
        """Configuración inicial del test"""
        # Usuario admin para auditoría
        self.admin = User.objects.create_user(
            rut='11111111-1',
            nombre='Admin',
            apellido_paterno='Test',
            email='admin@test.cl',
            password='testpass123'
        )
        
        # Datos geográficos
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        
        # Tipo y dependencia
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        # Ciclos académicos
        self.ciclo_2024 = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2024',
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 20),
            estado='ACTIVO',
            creado_por=self.admin,
            modificado_por=self.admin
        )
        
        self.ciclo_2023 = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2023',
            fecha_inicio=date(2023, 3, 1),
            fecha_fin=date(2023, 12, 20),
            estado='CERRADO',
            creado_por=self.admin,
            modificado_por=self.admin
        )
        
        # Nivel y curso
        self.nivel = NivelEducativo.objects.create(nombre='Enseñanza Media')
        self.curso_activo = Curso.objects.create(colegio=self.colegio,
            nivel=self.nivel,
            nombre='Primero A',
            ciclo_academico=self.ciclo_2024,
            activo=True
        )
        
        self.curso_inactivo = Curso.objects.create(colegio=self.colegio,
            nivel=self.nivel,
            nombre='Primero A (2023)',
            ciclo_academico=self.ciclo_2023,
            activo=False
        )
        
        # Roles
        self.rol_estudiante = Role.objects.create(nombre='estudiante')
        
        # Estudiante
        self.estudiante = User.objects.create_user(
            rut='12345678-9',
            nombre='Juan',
            apellido_paterno='Pérez',
            email='juan@test.cl',
            password='testpass123',
            role=self.rol_estudiante,
            rbd_colegio=self.colegio.rbd
        )

    def test_audit_detecta_matricula_con_curso_inactivo(self):
        """Audit debe detectar matrícula ACTIVA con curso inactivo"""
        # Crear curso activo temporalmente
        curso_temp = Curso.objects.create(
            colegio=self.colegio,
            nivel=self.nivel,
            nombre='Temporal activo',
            ciclo_academico=self.ciclo_2023,
            activo=True
        )
        
        # Crear matrícula con curso activo (estado válido)
        Matricula.objects.create(
            estudiante=self.estudiante,
            curso=curso_temp,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_2023,
            estado='ACTIVA'
        )
        
        # Desactivar curso para crear estado inválido
        Curso.objects.filter(pk=curso_temp.pk).update(activo=False)
        
        # Ejecutar audit
        command = AuditCommand()
        output = UTF8StringIO()
        command.stdout = output  # Asignar antes de llamar handle
        command.handle(format='json', output=None)

        # Parsear resultado
        issues = parse_audit_output(output.getvalue())
        self.assertIsNotNone(issues)

        # Verificar que detectó el problema
        self.assertGreater(issues['categories']['matriculas_invalidas']['count'], 0)

    def test_audit_detecta_matricula_con_ciclo_cerrado(self):
        """Audit debe detectar matrícula ACTIVA con ciclo CERRADO"""
        # Crear curso activo temporalmente
        curso_temp = Curso.objects.create(
            colegio=self.colegio,
            nivel=self.nivel,
            nombre='Temporal activo 2',
            ciclo_academico=self.ciclo_2023,
            activo=True
        )
        
        # Crear matrícula con curso activo (estado válido)
        Matricula.objects.create(
            estudiante=self.estudiante,
            curso=curso_temp,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_2023,
            estado='ACTIVA'
        )
        
        # Desactivar curso para crear estado inválido
        Curso.objects.filter(pk=curso_temp.pk).update(activo=False)
        
        # Ejecutar audit
        command = AuditCommand()
        output = UTF8StringIO()
        command.stdout = output  # Asignar antes de llamar handle
        command.handle(format='json', output=None)
        
        # Parsear resultado
        issues = parse_audit_output(output.getvalue())
        self.assertIsNotNone(issues)
        
        # Verificar que detectó el problema
        self.assertGreater(issues['categories']['matriculas_invalidas']['count'], 0)

    def test_fix_suspende_matriculas_invalidas(self):
        """Fix debe suspender matrículas con curso/ciclo inválidos"""
        # Crear curso activo temporalmente
        curso_temp = Curso.objects.create(
            colegio=self.colegio,
            nivel=self.nivel,
            nombre='Temporal activo 3',
            ciclo_academico=self.ciclo_2023,
            activo=True
        )
        
        # Crear matrícula con curso activo (estado válido)
        matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            curso=curso_temp,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_2023,
            estado='ACTIVA'
        )
        
        # Desactivar curso para crear estado inválido
        Curso.objects.filter(pk=curso_temp.pk).update(activo=False)
        
        # Ejecutar fix con auto-confirm
        command = FixCommand()
        output = UTF8StringIO()
        command.handle(auto_confirm=True, dry_run=False, category=None, log_file=None, stdout=output)
        
        # Verificar que suspendió la matrícula
        matricula.refresh_from_db()
        self.assertEqual(matricula.estado, 'SUSPENDIDA')


class TestRegressionCursosConCicloInvalido(TestCase):
    """
    Test de regresión: Bug #2 - Cursos activos con ciclos no ACTIVO
    
    Escenario: Un curso está marcado como activo=True pero su ciclo_academico
    tiene estado diferente a 'ACTIVO' (CERRADO, FINALIZADO, etc.)
    
    Este bug causaba que dashboards mostraran cursos de años anteriores
    y que las validaciones fallaran silenciosamente.
    """

    def setUp(self):
        """Configuración inicial"""
        # Usuario admin para auditoría
        self.admin = User.objects.create_user(
            rut='11111111-1',
            nombre='Admin',
            apellido_paterno='Test',
            email='admin@test.cl',
            password='testpass123'
        )
        
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        self.ciclo_cerrado = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2023',
            fecha_inicio=date(2023, 3, 1),
            fecha_fin=date(2023, 12, 20),
            estado='CERRADO',
            creado_por=self.admin,
            modificado_por=self.admin
        )
        
        self.nivel = NivelEducativo.objects.create(nombre='Enseñanza Media')

    def test_audit_detecta_curso_activo_con_ciclo_cerrado(self):
        """Audit debe detectar curso activo=True con ciclo CERRADO"""
        # Crear curso activo con ciclo cerrado (BUG)
        Curso.objects.create(colegio=self.colegio,
            nivel=self.nivel,
            nombre='Primero A',
            ciclo_academico=self.ciclo_cerrado,
            activo=True  # BUG: activo pero ciclo cerrado
        )
        
        # Ejecutar audit
        command = AuditCommand()
        output = UTF8StringIO()
        command.stdout = output  # Asignar antes de llamar handle
        command.handle(format='json', output=None)
        
        # Parsear resultado
        issues = parse_audit_output(output.getvalue())
        self.assertIsNotNone(issues)
        
        # Verificar detección
        self.assertGreater(issues['categories']['cursos_invalidos']['count'], 0)

    def test_fix_desactiva_cursos_con_ciclo_invalido(self):
        """Fix debe desactivar cursos con ciclo no ACTIVO"""
        curso = Curso.objects.create(colegio=self.colegio,
            nivel=self.nivel,
            nombre='Primero A',
            ciclo_academico=self.ciclo_cerrado,
            activo=True
        )
        
        # Ejecutar fix
        command = FixCommand()
        output = UTF8StringIO()
        command.handle(auto_confirm=True, dry_run=False, category=None, log_file=None, stdout=output)
        
        # Verificar desactivación
        curso.refresh_from_db()
        self.assertFalse(curso.activo)


class TestRegressionClasesInvalidas(TestCase):
    """
    Test de regresión: Bug #3 - Clases activas con relaciones inválidas
    
    Escenario: Una clase está marcada como activa=True pero:
    - Su curso está inactivo, O
    - Su profesor no existe o está inactivo, O
    - Su asignatura no existe
    
    Este bug causaba errores en registro de asistencia y notas.
    """

    def setUp(self):
        """Configuración inicial"""
        # Usuario admin para auditoría
        self.admin = User.objects.create_user(
            rut='11111111-1',
            nombre='Admin',
            apellido_paterno='Test',
            email='admin@test.cl',
            password='testpass123'
        )
        
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        self.ciclo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2024',
            fecha_inicio=date(2024, 3, 1),
            fecha_fin=date(2024, 12, 20),
            estado='ACTIVO',
            creado_por=self.admin,
            modificado_por=self.admin
        )
        
        self.nivel = NivelEducativo.objects.create(nombre='Enseñanza Media')
        self.curso_inactivo = Curso.objects.create(colegio=self.colegio,
            nivel=self.nivel,
            nombre='Primero A',
            ciclo_academico=self.ciclo,
            activo=False
        )
        
        self.asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre='Matemáticas'
        )
        
        self.rol_profesor = Role.objects.create(nombre='profesor')
        self.profesor = User.objects.create_user(
            rut='22222222-2',
            nombre='María',
            apellido_paterno='González',
            email='maria@test.cl',
            password='testpass123',
            role=self.rol_profesor,
            rbd_colegio=self.colegio.rbd
        )

    def test_audit_detecta_clase_activa_con_curso_inactivo(self):
        """Audit debe detectar clase activa con curso inactivo"""
        # Crear curso activo temporalmente
        curso_temp = Curso.objects.create(
            colegio=self.colegio,
            nivel=self.nivel,
            nombre='Temporal activo clase',
            ciclo_academico=self.ciclo,
            activo=True
        )
        
        # Crear clase con curso activo (estado válido)
        clase = Clase.objects.create(
            curso=curso_temp,
            asignatura=self.asignatura,
            profesor=self.profesor,
            colegio=self.colegio,
            activo=True
        )
        
        # Desactivar curso para crear estado inválido
        Curso.objects.filter(pk=curso_temp.pk).update(activo=False)
        
        # Ejecutar audit
        command = AuditCommand()
        output = UTF8StringIO()
        command.stdout = output  # Asignar antes de llamar handle
        command.handle(format='json', output=None)
        
        # Parsear resultado
        issues = parse_audit_output(output.getvalue())
        self.assertIsNotNone(issues)
        
        # Verificar detección
        self.assertGreater(issues['categories']['clases_invalidas']['count'], 0)

    def test_fix_desactiva_clases_invalidas(self):
        """Fix debe desactivar clases con relaciones inválidas"""
        # Crear curso activo temporalmente
        curso_temp = Curso.objects.create(
            colegio=self.colegio,
            nivel=self.nivel,
            nombre='Temporal activo clase 2',
            ciclo_academico=self.ciclo,
            activo=True
        )
        
        # Crear clase con curso activo (estado válido)
        clase = Clase.objects.create(
            curso=curso_temp,
            asignatura=self.asignatura,
            profesor=self.profesor,
            colegio=self.colegio,
            activo=True
        )
        
        # Desactivar curso para crear estado inválido
        Curso.objects.filter(pk=curso_temp.pk).update(activo=False)
        
        # Ejecutar fix
        command = FixCommand()
        output = UTF8StringIO()
        command.handle(auto_confirm=True, dry_run=False, category=None, log_file=None, stdout=output)
        
        # Verificar desactivación
        clase.refresh_from_db()
        self.assertFalse(clase.activo)


class TestRegressionUsersColegioHuerfano(TestCase):
    """
    Test de regresión: Bug #4 - Users con rbd_colegio huérfano
    
    Escenario: Un usuario tiene un valor en rbd_colegio pero ese colegio no existe
    en la base de datos.
    
    Este bug causaba errores en dashboards y operaciones que dependían del colegio.
    """

    def setUp(self):
        """Configuración inicial"""
        self.rol = Role.objects.create(nombre='estudiante')

    def test_audit_detecta_user_con_colegio_inexistente(self):
        """Audit debe detectar users con rbd_colegio huérfano"""
        # Crear user con colegio inexistente (BUG)
        User.objects.create_user(
            rut='12345678-9',
            nombre='Juan',
            apellido_paterno='Pérez',
            email='juan@test.cl',
            password='testpass123',
            role=self.rol,
            rbd_colegio=99999  # Colegio no existe
        )
        
        # Ejecutar audit
        command = AuditCommand()
        output = UTF8StringIO()
        command.stdout = output  # Asignar antes de llamar handle
        command.handle(format='json', output=None)
        
        # Parsear resultado
        issues = parse_audit_output(output.getvalue())
        self.assertIsNotNone(issues)
        
        # Verificar detección
        self.assertGreater(issues['categories']['usuarios_huerfanos']['count'], 0)

    def test_fix_limpia_rbd_colegio_huerfano(self):
        """Fix debe limpiar rbd_colegio cuando el colegio no existe"""
        user = User.objects.create_user(
            rut='12345678-9',
            nombre='Juan',
            apellido_paterno='Pérez',
            email='juan@test.cl',
            password='testpass123',
            role=self.rol,
            rbd_colegio=99999
        )
        
        # Ejecutar fix
        command = FixCommand()
        output = UTF8StringIO()
        command.handle(auto_confirm=True, dry_run=False, category=None, log_file=None, stdout=output)
        
        # Verificar limpieza
        user.refresh_from_db()
        self.assertIsNone(user.rbd_colegio)


class TestRegressionPerfilesCicloInvalido(TestCase):
    """
    Test de regresión: Bug #5 - Perfiles estudiante con ciclos inválidos
    
    Escenario: Un perfil de estudiante tiene ciclo_actual que:
    - No existe, O
    - No pertenece al colegio del estudiante, O
    - Está en estado CERRADO/FINALIZADO
    
    Este bug causaba errores en matrículas y consultas de estudiantes activos.
    """

    def setUp(self):
        """Configuración inicial"""
        # Usuario admin para auditoría
        self.admin = User.objects.create_user(
            rut='11111111-1',
            nombre='Admin',
            apellido_paterno='Test',
            email='admin@test.cl',
            password='testpass123'
        )
        
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        self.ciclo_cerrado = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2023',
            fecha_inicio=date(2023, 3, 1),
            fecha_fin=date(2023, 12, 20),
            estado='CERRADO',
            creado_por=self.admin,
            modificado_por=self.admin
        )
        
        self.rol = Role.objects.create(nombre='estudiante')
        self.estudiante = User.objects.create_user(
            rut='12345678-9',
            nombre='Juan',
            apellido_paterno='Pérez',
            email='juan@test.cl',
            password='testpass123',
            role=self.rol,
            rbd_colegio=self.colegio.rbd
        )

    def test_audit_detecta_perfil_con_ciclo_cerrado(self):
        """Audit debe detectar perfil con ciclo_actual CERRADO"""
        # Crear perfil con ciclo cerrado (BUG)
        PerfilEstudiante.objects.create(user=self.estudiante,
            ciclo_actual=self.ciclo_cerrado
        )
        
        # Ejecutar audit
        command = AuditCommand()
        output = UTF8StringIO()
        command.stdout = output  # Asignar antes de llamar handle
        command.handle(format='json', output=None)
        
        # Parsear resultado
        issues = parse_audit_output(output.getvalue())
        self.assertIsNotNone(issues)
        
        # Verificar detección
        self.assertGreater(issues['categories']['perfiles_estudiante_invalidos']['count'], 0)

    def test_fix_limpia_ciclo_invalido(self):
        """Fix debe limpiar ciclo_actual cuando no es ACTIVO"""
        perfil = PerfilEstudiante.objects.create(user=self.estudiante,
            ciclo_actual=self.ciclo_cerrado
        )
        
        # Ejecutar fix
        command = FixCommand()
        output = UTF8StringIO()
        command.handle(auto_confirm=True, dry_run=False, category=None, log_file=None, stdout=output)
        
        # Verificar limpieza
        perfil.refresh_from_db()
        self.assertIsNone(perfil.ciclo_actual)


class TestRegressionValidacionesDefensivas(TestCase):
    """
    Test de regresión: Validaciones defensivas implementadas
    
    Valida que las validaciones defensivas en servicios previenen
    que los bugs se manifiesten en operaciones reales.
    """

    def setUp(self):
        """Configuración inicial"""
        # Usuario admin para auditoría
        self.admin = User.objects.create_user(
            rut='11111111-1',
            nombre='Admin',
            apellido_paterno='Test',
            email='admin@test.cl',
            password='testpass123'
        )
        
        self.region = Region.objects.create(nombre='Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        self.tipo_est = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_est,
            dependencia=self.dependencia
        )
        
        # Solo ciclo cerrado
        self.ciclo_cerrado = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2023',
            fecha_inicio=date(2023, 3, 1),
            fecha_fin=date(2023, 12, 20),
            estado='CERRADO',
            creado_por=self.admin,
            modificado_por=self.admin
        )
        
        self.rol = Role.objects.create(nombre='estudiante')
        self.estudiante = User.objects.create_user(
            rut='12345678-9',
            nombre='Juan',
            apellido_paterno='Pérez',
            email='juan@test.cl',
            password='testpass123',
            role=self.rol,
            rbd_colegio=self.colegio.rbd
        )

    def test_validacion_impide_operaciones_sin_ciclo_activo(self):
        """
        Validaciones defensivas deben impedir operaciones cuando no hay ciclo activo.
        
        Este test confirma que el bug #2 está efectivamente prevenido a nivel de servicio.
        """
        from backend.apps.matriculas.services.matriculas_service import MatriculasService
        from backend.common.exceptions import PrerequisiteException
        
        # Intentar obtener matrícula sin ciclo activo debe lanzar PrerequisiteException
        with self.assertRaises(PrerequisiteException) as context:
            MatriculasService._validate_colegio_has_active_ciclo(self.colegio.rbd)
        
        # Verificar que sea el error correcto
        self.assertEqual(context.exception.error_type, 'MISSING_CICLO_ACTIVO')

    def test_validacion_impide_operaciones_sin_perfil(self):
        """
        Validaciones defensivas deben impedir operaciones cuando estudiante no tiene perfil.
        
        Este test confirma que el bug #5 está efectivamente prevenido a nivel de servicio.
        """
        from backend.apps.matriculas.services.matriculas_service import MatriculasService
        from backend.common.exceptions import PrerequisiteException
        
        # Intentar validar estudiante sin perfil debe lanzar PrerequisiteException
        with self.assertRaises(PrerequisiteException) as context:
            MatriculasService._validate_student_profile(self.estudiante)
        
        # Verificar que sea el error correcto
        self.assertEqual(context.exception.error_type, 'INVALID_STATE')
        self.assertIn('perfil', context.exception.error['context']['message'].lower())









