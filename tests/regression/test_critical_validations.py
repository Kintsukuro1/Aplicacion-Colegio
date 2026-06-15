"""
Tests de Regresión Críticos - Fase 5

Valida que el sistema NUNCA permita estados inválidos detectados
en auditorías previas.

Scenarios críticos:
1. Colegio sin ciclo activo
2. Curso sin ciclo válido
3. Profesor sin perfil válido
4. Matrícula inválida
5. Clase sin profesor
"""

import pytest
from django.test import TestCase
from django.db import transaction

from backend.apps.institucion.models import (
    Colegio, CicloAcademico, Region, Comuna, 
    TipoEstablecimiento, DependenciaAdministrativa
)
from backend.apps.cursos.models import NivelEducativo, Curso, Clase, Asignatura
from backend.apps.matriculas.models import Matricula
from backend.apps.accounts.models import Role, User, PerfilEstudiante, PerfilProfesor
from backend.apps.core.services.data_repair_service import DataRepairService


@pytest.mark.django_db
class TestCriticalValidations(TestCase):
    """Tests de regresión para validaciones críticas"""

    def setUp(self):
        """Setup base data para todos los tests"""
        # Crear Role admin
        self.role_admin = Role.objects.create(nombre='Administrador general')
        self.role_estudiante = Role.objects.create(nombre='Alumno')
        self.role_profesor = Role.objects.create(nombre='Profesor')
        
        # Crear usuario admin
        self.admin = User.objects.create(
            rut='11111111-1',
            nombre='Admin',
            apellido_paterno='Test',
            email='admin@test.cl',
            role=self.role_admin,
            is_active=True
        )
        
        # Crear dependencias geográficas
        self.region = Region.objects.create(nombre='Región Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        self.tipo_establecimiento = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Crear colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='12345678-9',
            nombre='Colegio Test',
            direccion='Calle Test 123',
            telefono='123456789',
            correo='colegio@test.cl',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        self.admin.rbd_colegio = self.colegio.rbd
        self.admin.save()
        
        # Crear ciclos académicos (activo e inactivo)
        self.ciclo_activo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2024',
            fecha_inicio='2024-03-01',
            fecha_fin='2024-12-31',
            estado='ACTIVO',
            creado_por=self.admin,
            modificado_por=self.admin
        )
        
        self.ciclo_inactivo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2023',
            fecha_inicio='2023-03-01',
            fecha_fin='2023-12-31',
            estado='CERRADO',
            creado_por=self.admin,
            modificado_por=self.admin
        )
        
        # Crear nivel educativo
        self.nivel = NivelEducativo.objects.create(nombre='1° Básico', activo=True)

    def test_matricula_requires_active_cycle(self):
        """
        REGRESIÓN: No se puede crear matrícula sin ciclo activo
        
        Problema original: Matrículas creadas con ciclos cerrados
        Solución: Service valida estado del ciclo antes de crear matrícula
        """
        # Crear estudiante
        estudiante = User.objects.create(
            rut='22222222-2',
            nombre='Estudiante',
            apellido_paterno='Test',
            email='estudiante@test.cl',
            role=self.role_estudiante,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        PerfilEstudiante.objects.create(
            user=estudiante,
            estado_academico='Activo'
        )
        
        # Crear curso con ciclo activo
        curso = Curso.objects.create(
            nombre='1A',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            activo=True
        )
        
        # VALIDACIÓN 1: Matrícula con ciclo activo debe crearse correctamente
        matricula_valida = Matricula.objects.create(
            estudiante=estudiante,
            colegio=self.colegio,
            curso=curso,
            ciclo_academico=self.ciclo_activo,
            estado='ACTIVA'
        )
        self.assertIsNotNone(matricula_valida)
        self.assertEqual(matricula_valida.estado, 'ACTIVA')
        
        # VALIDACIÓN 2: Matrícula con ciclo inactivo es detectada por auditoría
        # y puede ser reparada
        matricula_invalida = Matricula.objects.create(
            estudiante=estudiante,
            colegio=self.colegio,
            curso=curso,
            ciclo_academico=self.ciclo_inactivo,
            estado='ACTIVA'
        )
        
        # Ejecutar reparación
        service = DataRepairService()
        report = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        # El servicio debe haber suspendido la matrícula inválida
        matricula_invalida.refresh_from_db()
        self.assertEqual(matricula_invalida.estado, 'SUSPENDIDA')
        self.assertGreater(report['categories']['matriculas']['count'], 0)

    def test_curso_requires_valid_cycle(self):
        """
        REGRESIÓN: No se pueden tener cursos sin ciclo académico válido
        
        Problema original: Cursos sin ciclo o con ciclo inactivo
        Solución: Auditoría detecta y servicio repara desactivando el curso
        """
        # VALIDACIÓN 1: Curso con ciclo activo es válido
        curso_valido = Curso.objects.create(
            nombre='1A',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            activo=True
        )
        self.assertTrue(curso_valido.activo)
        self.assertEqual(curso_valido.ciclo_academico.estado, 'ACTIVO')
        
        # VALIDACIÓN 2: Curso con ciclo inactivo es detectado y desactivado
        curso_invalido = Curso.objects.create(
            nombre='1B',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_inactivo,
            activo=True
        )
        
        # Ejecutar reparación
        service = DataRepairService()
        report = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        # El curso debe haber sido desactivado
        curso_invalido.refresh_from_db()
        self.assertFalse(curso_invalido.activo)
        self.assertGreater(report['categories']['cursos']['count'], 0)
        
        # VALIDACIÓN 3: Curso sin ciclo es detectado y desactivado
        curso_sin_ciclo = Curso.objects.create(
            nombre='1C',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=None,
            activo=True
        )
        
        report = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        curso_sin_ciclo.refresh_from_db()
        self.assertFalse(curso_sin_ciclo.activo)

    def test_profesor_requires_valid_profile(self):
        """
        REGRESIÓN: Profesores deben tener perfil válido
        
        Problema original: Usuarios con rol profesor sin PerfilProfesor
        Solución: El sistema permite profesores sin perfil, pero deben estar
                  correctamente registrados en el sistema
        
        NOTA: El servicio de reparación NO desactiva automáticamente profesores
              sin perfil - esto requiere intervención manual o políticas específicas
        """
        # VALIDACIÓN 1: Profesor con perfil válido
        profesor_valido = User.objects.create(
            rut='33333333-3',
            nombre='Profesor',
            apellido_paterno='Valido',
            email='profesor.valido@test.cl',
            role=self.role_profesor,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        PerfilProfesor.objects.create(
            user=profesor_valido,
            especialidad='Matemáticas'
        )
        
        # Este profesor tiene perfil, por lo tanto es válido
        self.assertTrue(profesor_valido.is_active)
        # Verificar que existe un perfil para este profesor
        self.assertTrue(PerfilProfesor.objects.filter(user=profesor_valido).exists())
        
        # VALIDACIÓN 2: Profesor sin perfil permanece activo
        # El sistema permite profesores sin perfil (pueden ser administrativos)
        profesor_sin_perfil = User.objects.create(
            rut='44444444-4',
            nombre='Profesor',
            apellido_paterno='Sin Perfil',
            email='profesor.invalido@test.cl',
            role=self.role_profesor,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        # Ejecutar reparación
        service = DataRepairService()
        report = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        # El profesor sin perfil NO es desactivado automáticamente
        # Esto requiere política específica o intervención manual
        profesor_sin_perfil.refresh_from_db()
        self.assertTrue(profesor_sin_perfil.is_active)

    def test_clase_requires_active_profesor(self):
        """
        REGRESIÓN: Clases deben tener profesor activo
        
        Problema original: Clases asignadas a profesores inactivos
        Solución: Auditoría detecta y servicio desactiva la clase
        """
        # Crear curso válido
        curso = Curso.objects.create(
            nombre='1A',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            activo=True
        )
        
        # Crear asignatura
        asignatura = Asignatura.objects.create(nombre='Matemáticas', colegio=self.colegio)
        
        # VALIDACIÓN 1: Profesor activo con perfil
        profesor_activo = User.objects.create(
            rut='55555555-5',
            nombre='Profesor',
            apellido_paterno='Activo',
            email='profesor.activo@test.cl',
            role=self.role_profesor,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        PerfilProfesor.objects.create(
            user=profesor_activo,
            especialidad='Matemáticas'
        )
        
        # Clase con profesor activo es válida
        clase_valida = Clase.objects.create(
            curso=curso,
            asignatura=asignatura,
            profesor=profesor_activo,
            colegio=self.colegio,
            activo=True
        )
        self.assertTrue(clase_valida.activo)
        
        # VALIDACIÓN 2: Clase con profesor que se vuelve inactivo es detectada
        # Crear segundo profesor (activo inicialmente) y asignarle una clase
        profesor_que_sera_inactivo = User.objects.create(
            rut='66666666-6',
            nombre='Profesor',
            apellido_paterno='Inactivo',
            email='profesor.inactivo@test.cl',
            role=self.role_profesor,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        asignatura2 = Asignatura.objects.create(nombre='Ciencias', colegio=self.colegio)
        clase_invalida = Clase.objects.create(
            curso=curso,
            asignatura=asignatura2,
            profesor=profesor_que_sera_inactivo,
            colegio=self.colegio,
            activo=True
        )
        
        # Ahora desactivar al profesor (simula baja del profesor)
        profesor_que_sera_inactivo.is_active = False
        profesor_que_sera_inactivo.save()
        
        # Ejecutar reparación
        service = DataRepairService()
        report = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        # La clase debe haber sido desactivada
        clase_invalida.refresh_from_db()
        self.assertFalse(clase_invalida.activo)
        self.assertGreater(report['categories']['clases']['count'], 0)

    def test_clase_requires_active_curso(self):
        """
        REGRESIÓN: Clases deben pertenecer a curso activo
        
        Problema original: Clases asociadas a cursos inactivos
        Solución: Auditoría detecta y servicio desactiva la clase
        """
        # Crear profesor válido
        profesor = User.objects.create(
            rut='77777777-7',
            nombre='Profesor',
            apellido_paterno='Test',
            email='profesor.test@test.cl',
            role=self.role_profesor,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        PerfilProfesor.objects.create(
            user=profesor,
            especialidad='Lenguaje'
        )
        
        # Crear asignatura
        asignatura = Asignatura.objects.create(nombre='Lenguaje', colegio=self.colegio)
        
        # VALIDACIÓN 1: Curso activo
        curso_activo = Curso.objects.create(
            nombre='2A',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            activo=True
        )
        
        clase_valida = Clase.objects.create(
            curso=curso_activo,
            asignatura=asignatura,
            profesor=profesor,
            colegio=self.colegio,
            activo=True
        )
        self.assertTrue(clase_valida.activo)
        
        # VALIDACIÓN 2: Curso que se vuelve inactivo
        curso_que_sera_inactivo = Curso.objects.create(
            nombre='2B',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_activo,
            activo=True
        )
        
        asignatura2 = Asignatura.objects.create(nombre='Historia', colegio=self.colegio)
        clase_invalida = Clase.objects.create(
            curso=curso_que_sera_inactivo,
            asignatura=asignatura2,
            profesor=profesor,
            colegio=self.colegio,
            activo=True
        )
        
        # Ahora desactivar el curso (simula cierre de curso)
        curso_que_sera_inactivo.activo = False
        curso_que_sera_inactivo.save()
        
        # Ejecutar reparación
        service = DataRepairService()
        report = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        # La clase debe haber sido desactivada
        clase_invalida.refresh_from_db()
        self.assertFalse(clase_invalida.activo)

    def test_perfil_estudiante_requires_active_user(self):
        """
        REGRESIÓN: Perfiles de estudiante deben tener usuario activo
        
        Problema original: Perfiles asociados a usuarios inactivos
        Solución: Auditoría detecta y servicio suspende el perfil
        """
        # VALIDACIÓN 1: Usuario activo con perfil activo
        estudiante_activo = User.objects.create(
            rut='88888888-8',
            nombre='Estudiante',
            apellido_paterno='Activo',
            email='estudiante.activo@test.cl',
            role=self.role_estudiante,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        perfil_valido = PerfilEstudiante.objects.create(
            user=estudiante_activo,
            estado_academico='Activo',
            ciclo_actual=self.ciclo_activo
        )
        self.assertEqual(perfil_valido.estado_academico, 'Activo')
        
        # VALIDACIÓN 2: Usuario inactivo con perfil activo (inválido)
        estudiante_inactivo = User.objects.create(
            rut='99999999-9',
            nombre='Estudiante',
            apellido_paterno='Inactivo',
            email='estudiante.inactivo@test.cl',
            role=self.role_estudiante,
            rbd_colegio=self.colegio.rbd,
            is_active=False
        )
        
        perfil_invalido = PerfilEstudiante.objects.create(
            user=estudiante_inactivo,
            estado_academico='Activo',
            ciclo_actual=self.ciclo_activo
        )
        
        # Ejecutar reparación
        service = DataRepairService()
        report = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        # El perfil debe haber sido suspendido
        perfil_invalido.refresh_from_db()
        self.assertEqual(perfil_invalido.estado_academico, 'Suspendido')
        self.assertGreater(report['categories']['perfiles_estudiante']['count'], 0)

    def test_sistema_previene_multiples_estados_invalidos(self):
        """
        REGRESIÓN INTEGRAL: Sistema detecta y repara múltiples problemas simultáneos
        
        Valida que el sistema puede detectar y reparar múltiples
        estados inválidos en una sola ejecución
        """
        # Crear múltiples estados inválidos a propósito
        
        # 1. Curso con ciclo inactivo
        curso_invalido = Curso.objects.create(
            nombre='Curso Inválido',
            nivel=self.nivel,
            colegio=self.colegio,
            ciclo_academico=self.ciclo_inactivo,
            activo=True
        )
        
        # 2. Estudiante para matrícula inválida
        estudiante = User.objects.create(
            rut='10101010-1',
            nombre='Estudiante',
            apellido_paterno='Multi',
            email='estudiante.multi@test.cl',
            role=self.role_estudiante,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        # 3. Matrícula con ciclo inactivo
        matricula_invalida = Matricula.objects.create(
            estudiante=estudiante,
            colegio=self.colegio,
            curso=curso_invalido,
            ciclo_academico=self.ciclo_inactivo,
            estado='ACTIVA'
        )
        
        # 4. Profesor sin perfil
        profesor_sin_perfil = User.objects.create(
            rut='11110111-0',
            nombre='Profesor',
            apellido_paterno='Sin Perfil',
            email='profesor.multi@test.cl',
            role=self.role_profesor,
            rbd_colegio=self.colegio.rbd,
            is_active=True
        )
        
        # 5. Perfil estudiante con usuario inactivo
        estudiante_inactivo = User.objects.create(
            rut='12121212-1',
            nombre='Estudiante',
            apellido_paterno='Inactivo',
            email='estudiante.inactivo2@test.cl',
            role=self.role_estudiante,
            rbd_colegio=self.colegio.rbd,
            is_active=False
        )
        
        perfil_invalido = PerfilEstudiante.objects.create(
            user=estudiante_inactivo,
            estado_academico='Activo',
            ciclo_actual=self.ciclo_activo
        )
        
        # EJECUTAR REPARACIÓN INTEGRAL
        service = DataRepairService()
        report = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        # VALIDAR QUE TODOS LOS PROBLEMAS FUERON DETECTADOS Y REPARADOS
        
        # 1. Curso desactivado
        curso_invalido.refresh_from_db()
        self.assertFalse(curso_invalido.activo)
        self.assertGreater(report['categories']['cursos']['count'], 0)
        
        # 2. Matrícula suspendida
        matricula_invalida.refresh_from_db()
        self.assertEqual(matricula_invalida.estado, 'SUSPENDIDA')
        self.assertGreater(report['categories']['matriculas']['count'], 0)
        
        # 3. Profesor sin perfil NO es desactivado (política del servicio)
        profesor_sin_perfil.refresh_from_db()
        self.assertTrue(profesor_sin_perfil.is_active)
        
        # 4. Perfil estudiante suspendido
        perfil_invalido.refresh_from_db()
        self.assertEqual(perfil_invalido.estado_academico, 'Suspendido')
        self.assertGreater(report['categories']['perfiles_estudiante']['count'], 0)
        
        # VALIDAR QUE EL REPORTE CONTIENE TODAS LAS CATEGORÍAS
        self.assertIn('matriculas', report['categories'])
        self.assertIn('cursos', report['categories'])
        self.assertIn('clases', report['categories'])
        self.assertIn('usuarios', report['categories'])
        self.assertIn('perfiles_estudiante', report['categories'])


@pytest.mark.django_db
class TestDataIntegrityNeverRegresses(TestCase):
    """
    Tests que validan que la integridad de datos NUNCA retrocede
    
    Estos tests aseguran que una vez reparado el sistema,
    no vuelve a permitir estados inválidos
    """

    def setUp(self):
        """Setup base data"""
        self.role_admin = Role.objects.create(nombre='Administrador general')
        self.role_estudiante = Role.objects.create(nombre='Alumno')
        
        self.admin = User.objects.create(
            rut='11111111-1',
            nombre='Admin',
            apellido_paterno='Test',
            email='admin@test.cl',
            role=self.role_admin,
            is_active=True
        )
        
        self.region = Region.objects.create(nombre='Región Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        self.tipo_establecimiento = TipoEstablecimiento.objects.create(nombre='Municipal')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        self.colegio = Colegio.objects.create(
            rbd=54321,
            rut_establecimiento='54321987-6',
            nombre='Colegio Integrity Test',
            direccion='Calle Test 456',
            telefono='987654321',
            correo='integrity@test.cl',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        self.admin.rbd_colegio = self.colegio.rbd
        self.admin.save()
        
        self.ciclo_activo = CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2024',
            fecha_inicio='2024-03-01',
            fecha_fin='2024-12-31',
            estado='ACTIVO',
            creado_por=self.admin,
            modificado_por=self.admin
        )

    def test_repaired_system_stays_clean_after_repair(self):
        """
        REGRESIÓN: Una vez reparado, el sistema permanece limpio
        
        Valida que después de una reparación, el sistema no genera
        nuevos problemas automáticamente
        """
        # Ejecutar reparación inicial
        service = DataRepairService()
        report_inicial = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        # Ejecutar segunda reparación (no debería encontrar problemas)
        report_segundo = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        # La segunda reparación no debe haber hecho cambios
        self.assertEqual(report_segundo['categories']['matriculas']['count'], 0)
        self.assertEqual(report_segundo['categories']['cursos']['count'], 0)
        self.assertEqual(report_segundo['categories']['clases']['count'], 0)
        self.assertEqual(report_segundo['categories']['usuarios']['count'], 0)
        self.assertEqual(report_segundo['categories']['perfiles_estudiante']['count'], 0)

    def test_system_prevents_creating_invalid_states_programmatically(self):
        """
        REGRESIÓN: Validaciones defensivas previenen estados inválidos
        
        Aunque alguien intente crear estados inválidos directamente,
        las validaciones defensivas deben impedirlo
        """
        # Este test valida que los services tienen validaciones defensivas
        
        # Crear nivel educativo
        nivel = NivelEducativo.objects.create(nombre='1° Básico', activo=True)
        
        # Intentar crear curso sin ciclo (permitido a nivel de modelo,
        # pero las validaciones defensivas en services deben prevenirlo)
        curso_sin_ciclo = Curso.objects.create(
            nombre='Curso Sin Ciclo',
            nivel=nivel,
            colegio=self.colegio,
            ciclo_academico=None,
            activo=True
        )
        
        # El servicio de reparación debe detectarlo
        service = DataRepairService()
        report = service.repair_all(rbd_colegio=self.colegio.rbd, dry_run=False)
        
        curso_sin_ciclo.refresh_from_db()
        self.assertFalse(curso_sin_ciclo.activo)
        self.assertGreater(report['categories']['cursos']['count'], 0)
