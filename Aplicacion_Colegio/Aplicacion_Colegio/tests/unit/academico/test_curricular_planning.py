import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from backend.apps.institucion.models import (
    Colegio, Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa,
    NivelEducativo, CicloAcademico
)
from backend.apps.cursos.models import Curso, Asignatura, Clase
from backend.apps.accounts.models import Role, User
from backend.apps.academico.models import (
    ObjetivoAprendizaje, Rubrica, CriterioRubrica, NivelRubrica,
    Planificacion, Evaluacion, Calificacion
)
from backend.apps.academico.services.planning_curricular import PlanningCurricularService

pytestmark = pytest.mark.django_db


class TestCurricularPlanning(TestCase):
    """
    Suite de Pruebas Unitarias para el Módulo de Planificación Curricular
    y Banco de Recursos con Control Estricto Multi-Tenant.
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

        # 1. Crear Colegio A (RBD 1010)
        self.colegio_a = Colegio.objects.get_or_create(
            rbd=1010,
            defaults={
                'nombre': 'Colegio A',
                'rut_establecimiento': '10.010.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]

        # 2. Crear Colegio B (RBD 2020)
        self.colegio_b = Colegio.objects.get_or_create(
            rbd=2020,
            defaults={
                'nombre': 'Colegio B',
                'rut_establecimiento': '20.020.000-0',
                'comuna': comuna,
                'tipo_establecimiento': tipo,
                'dependencia': dependencia
            }
        )[0]

        # Roles
        self.rol_profesor = Role.objects.get_or_create(nombre='Profesor')[0]
        self.rol_coordinador = Role.objects.get_or_create(nombre='Coordinador')[0]

        # Profesores y Coordinadores
        self.profesor_a = User.objects.get_or_create(
            email='profe.a@colegio.cl',
            defaults={
                'rut': '11111111-1',
                'nombre': 'Profe A',
                'apellido_paterno': 'Docente',
                'role': self.rol_profesor,
                'rbd_colegio': 1010
            }
        )[0]

        self.profesor_b = User.objects.get_or_create(
            email='profe.b@colegio.cl',
            defaults={
                'rut': '22222222-2',
                'nombre': 'Profe B',
                'apellido_paterno': 'Docente',
                'role': self.rol_profesor,
                'rbd_colegio': 2020
            }
        )[0]

        self.coordinador_a = User.objects.get_or_create(
            email='coord.a@colegio.cl',
            defaults={
                'rut': '33333333-3',
                'nombre': 'Coord A',
                'apellido_paterno': 'Academico',
                'role': self.rol_coordinador,
                'rbd_colegio': 1010
            }
        )[0]

        # Ciclo Académico y Nivel Educativo
        self.nivel = NivelEducativo.objects.get_or_create(nombre='7° Básico')[0]
        
        self.ciclo_a = CicloAcademico.objects.create(
            colegio=self.colegio_a,
            nombre='2026',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            estado='ACTIVO'
        )
        self.ciclo_b = CicloAcademico.objects.create(
            colegio=self.colegio_b,
            nombre='2026',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            estado='ACTIVO'
        )

        # Cursos y Asignaturas
        self.curso_a = Curso.objects.get_or_create(
            nombre='7° Básico A',
            defaults={
                'colegio': self.colegio_a,
                'nivel': self.nivel,
                'ciclo_academico': self.ciclo_a,
                'activo': True
            }
        )[0]

        self.asignatura_a = Asignatura.objects.get_or_create(
            nombre='Ciencias Naturales',
            defaults={'colegio': self.colegio_a}
        )[0]

        # Clase (Profesor A, Asignatura A, Colegio A)
        self.clase_a = Clase.objects.get_or_create(
            curso=self.curso_a,
            asignatura=self.asignatura_a,
            profesor=self.profesor_a,
            defaults={'colegio': self.colegio_a, 'activo': True}
        )[0]

        # Clase para Profesor B (Colegio B)
        self.curso_b = Curso.objects.get_or_create(
            nombre='7° Básico B',
            defaults={
                'colegio': self.colegio_b,
                'nivel': self.nivel,
                'ciclo_academico': self.ciclo_b,
                'activo': True
            }
        )[0]

        self.asignatura_b = Asignatura.objects.get_or_create(
            nombre='Ciencias Naturales',
            defaults={'colegio': self.colegio_b}
        )[0]

        self.clase_b = Clase.objects.get_or_create(
            curso=self.curso_b,
            asignatura=self.asignatura_b,
            profesor=self.profesor_b,
            defaults={'colegio': self.colegio_b, 'activo': True}
        )[0]

        # Objetivos de Aprendizaje (OAs)
        self.oa_a1 = ObjetivoAprendizaje.objects.create(
            colegio=self.colegio_a,
            asignatura=self.asignatura_a,
            codigo='CN07_OA01',
            descripcion='Explicar el comportamiento de los gases',
            nivel='7° Básico',
            activo=True
        )

        self.oa_b1 = ObjetivoAprendizaje.objects.create(
            colegio=self.colegio_b,
            asignatura=self.asignatura_b,
            codigo='CN07_OA01',
            descripcion='Explicar el comportamiento de los gases',
            nivel='7° Básico',
            activo=True
        )

    def test_create_planificacion_valida(self):
        """Valida la correcta creación de una planificación en estado BORRADOR."""
        plan = PlanningCurricularService.create_planificacion(
            user=self.profesor_a,
            colegio_id=self.colegio_a.rbd,
            clase_id=self.clase_a.id,
            titulo='Unidad Gases 1',
            objetivo_general='Comprender la ley de gases ideales',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=15),
            objetivo_ids=[self.oa_a1.id_oa]
        )

        self.assertEqual(plan.titulo, 'Unidad Gases 1')
        self.assertEqual(plan.estado, 'BORRADOR')
        self.assertIn(self.oa_a1, plan.objetivos_aprendizaje.all())
        self.assertTrue(plan.activa)

    def test_multi_tenant_isolation_planning_creation(self):
        """Valida que Colegio A no pueda asociar un OA perteneciente a Colegio B."""
        with self.assertRaises(ValidationError):
            PlanningCurricularService.create_planificacion(
                user=self.profesor_a,
                colegio_id=self.colegio_a.rbd,
                clase_id=self.clase_a.id,
                titulo='Plan Fallido',
                objetivo_general='Malicioso',
                fecha_inicio=date.today(),
                fecha_fin=date.today() + timedelta(days=10),
                objetivo_ids=[self.oa_b1.id_oa]  # Pertenece a Colegio B
            )

    def test_planificacion_lifecycle_and_immutability(self):
        """Valida las transiciones de estado y la inmutabilidad de planificaciones aprobadas/enviadas."""
        # 1. Crear planificación
        plan = PlanningCurricularService.create_planificacion(
            user=self.profesor_a,
            colegio_id=self.colegio_a.rbd,
            clase_id=self.clase_a.id,
            titulo='Unidad 1',
            objetivo_general='Metas',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=5)
        )

        # 2. Enviar a revisión
        plan_enviado = PlanningCurricularService.enviar_planificacion(
            user=self.profesor_a,
            colegio_id=self.colegio_a.rbd,
            planificacion_id=plan.id_planificacion
        )
        self.assertEqual(plan_enviado.estado, 'ENVIADA')

        # 3. Intentar editar planificación enviada (debe arrojar ValidationError)
        with self.assertRaises(ValidationError):
            PlanningCurricularService.update_planificacion(
                user=self.profesor_a,
                colegio_id=self.colegio_a.rbd,
                planificacion_id=plan.id_planificacion,
                titulo='Edición no permitida',
                objetivo_general='Metas',
                fecha_inicio=date.today(),
                fecha_fin=date.today() + timedelta(days=5)
            )

        # 4. Coordinador aprueba
        plan_aprobado = PlanningCurricularService.revisar_planificacion(
            coordinador=self.coordinador_a,
            colegio_id=self.colegio_a.rbd,
            planificacion_id=plan.id_planificacion,
            aprobar=True,
            observaciones='Excelente trabajo curricular'
        )
        self.assertEqual(plan_aprobado.estado, 'APROBADA')

        # 5. Intentar eliminar planificación aprobada (debe arrojar ValidationError)
        with self.assertRaises(ValidationError):
            PlanningCurricularService.delete_planificacion(
                user=self.profesor_a,
                colegio_id=self.colegio_a.rbd,
                planificacion_id=plan.id_planificacion
            )

    def test_banco_rubricas_cloning(self):
        """Prueba la clonación y copiado estricto de rúbricasCriteria y Niveles entre profesores del mismo colegio/departamento."""
        # Profesor A crea una Rúbrica compartida en Colegio A
        rubrica_origen = Rubrica.objects.create(
            colegio=self.colegio_a,
            asignatura=self.asignatura_a,
            creado_por=self.profesor_a,
            nombre='Rúbrica Ciencias 7A',
            descripcion='Evalúa exposiciones de gases',
            es_compartida=True,
            activo=True
        )

        criterio = CriterioRubrica.objects.create(
            rubrica=rubrica_origen,
            nombre='Claridad Científica',
            descripcion='Explica con propiedad las leyes',
            peso=50.00,
            orden=1
        )

        NivelRubrica.objects.create(
            criterio=criterio,
            puntaje=3,
            descripcion='Excelente',
            orden=1
        )

        # Profesor A clona la rúbrica para su propia clase/uso
        rubrica_clonada = PlanningCurricularService.clone_rubrica(
            user=self.profesor_a,
            colegio_id=self.colegio_a.rbd,
            rubrica_id=rubrica_origen.id_rubrica,
            asignatura_id=self.asignatura_a.pk
        )

        # Aseveraciones sobre la copia
        self.assertNotEqual(rubrica_clonada.id_rubrica, rubrica_origen.id_rubrica)
        self.assertEqual(rubrica_clonada.nombre, f"Copia de {rubrica_origen.nombre}")
        self.assertFalse(rubrica_clonada.es_compartida) # Las copias son privadas por defecto

        # Verificar copias de criterios y niveles
        self.assertEqual(rubrica_clonada.criterios.count(), 1)
        criterio_clonado = rubrica_clonada.criterios.first()
        self.assertEqual(criterio_clonado.nombre, 'Claridad Científica')
        self.assertEqual(criterio_clonado.niveles.count(), 1)
        self.assertEqual(criterio_clonado.niveles.first().puntaje, 3)

    def test_banco_evaluaciones_cloning(self):
        """Prueba que la clonación de evaluaciones mantenga los campos originales y resetee las calificaciones a un estado limpio."""
        # Crear evaluación origen para Clase A
        evaluacion_origen = Evaluacion.objects.create(
            colegio=self.colegio_a,
            clase=self.clase_a,
            nombre='Solemne 1 Gases',
            fecha_evaluacion=date.today(),
            ponderacion=30.00,
            periodo='semestre1',
            tipo_evaluacion='sumativa',
            activa=True
        )

        # Insertar una calificación ficticia para verificar que la copia no herede calificaciones
        Calificacion.objects.create(
            colegio=self.colegio_a,
            evaluacion=evaluacion_origen,
            estudiante=self.profesor_a, # Mock student using User
            nota=6.5,
            registrado_por=self.profesor_a
        )

        # Profesor A clona esta evaluación para otra clase ficticia del mismo colegio (misma asignatura)
        clase_destino = Clase.objects.create(
            curso=self.curso_a,
            asignatura=self.asignatura_a,
            profesor=self.profesor_a,
            colegio=self.colegio_a,
            activo=True
        )

        fecha_nueva = date.today() + timedelta(days=20)
        evaluacion_clonada = PlanningCurricularService.clone_evaluacion(
            user=self.profesor_a,
            colegio_id=self.colegio_a.rbd,
            evaluacion_id=evaluacion_origen.id_evaluacion,
            target_clase_id=clase_destino.id,
            fecha_evaluacion=fecha_nueva
        )

        # Comprobaciones
        self.assertEqual(evaluacion_clonada.nombre, f"Copia de {evaluacion_origen.nombre}")
        self.assertEqual(evaluacion_clonada.clase, clase_destino)
        self.assertEqual(evaluacion_clonada.fecha_evaluacion, fecha_nueva)
        self.assertEqual(evaluacion_clonada.ponderacion, 30.00)

        # Comprobar estado limpio: la nueva evaluación no debe tener ninguna calificación
        self.assertEqual(Calificacion.objects.filter(evaluacion=evaluacion_clonada).count(), 0)
