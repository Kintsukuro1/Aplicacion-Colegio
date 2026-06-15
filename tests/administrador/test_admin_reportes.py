"""
Tests de generación de reportes para administradores
"""
from datetime import date
from decimal import Decimal
from tests.common.test_base import BaseTestCase
from backend.apps.accounts.models import User
from backend.apps.cursos.models import Curso, Clase, Asignatura
from backend.apps.academico.models import Evaluacion, Calificacion, Asistencia


class AdministradorReportesTest(BaseTestCase):
    """Tests de funcionalidad de reportes del administrador"""
    
    def setUp(self):
        super().setUp()
        self.user_admin = self.crear_usuario_admin()
        self.user_profesor = self.crear_usuario_profesor()
        
        # Crear asignatura y clase para tests
        self.asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre="Matemáticas",
            codigo="MAT101",
            horas_semanales=4,
            activa=True
        )
        
        self.clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=self.asignatura,
            profesor=self.user_profesor,
            activo=True
        )
    
    def test_admin_puede_contar_total_usuarios(self):
        """Verificar que un administrador puede contar el total de usuarios"""
        # Crear varios usuarios
        for i in range(5):
            self.crear_usuario_estudiante(
                email=f"est_total{i}@test.cl",
                rut=f"3030303{i}-{i}"
            )
        
        total_usuarios = User.objects.filter(rbd_colegio=self.colegio.rbd).count()
        
        self.assertGreaterEqual(total_usuarios, 6)  # admin + profesor + 5 estudiantes (mínimo)
    
    def test_admin_puede_generar_reporte_asistencia_general(self):
        """Verificar que un administrador puede generar reporte de asistencia general"""
        # Crear estudiantes
        estudiantes = []
        for i in range(3):
            est, _ = self.crear_usuario_estudiante(
                email=f"est_asist_rep{i}@test.cl",
                rut=f"4040404{i}-{i}"
            )
            estudiantes.append(est)
        
        # Registrar asistencia
        for est in estudiantes:
            Asistencia.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                estudiante=est,
                fecha=date.today(),
                estado='P',
                tipo_asistencia='Presencial'
            )
        
        # Generar reporte
        total_asistencias = Asistencia.objects.filter(
            colegio=self.colegio,
            fecha=date.today()
        ).count()
        
        presentes = Asistencia.objects.filter(
            colegio=self.colegio,
            fecha=date.today(),
            estado='P'
        ).count()
        
        self.assertEqual(total_asistencias, 3)
        self.assertEqual(presentes, 3)
    
    def test_admin_puede_calcular_promedio_general_curso(self):
        """Verificar que un administrador puede calcular el promedio general de un curso"""
        # Crear evaluación
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Global",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('100.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        # Crear estudiantes y calificaciones
        notas = [Decimal('6.0'), Decimal('5.5'), Decimal('6.5')]
        for i, nota in enumerate(notas):
            est, _ = self.crear_usuario_estudiante(
                email=f"est_prom{i}@test.cl",
                rut=f"5050505{i}-{i}"
            )
            
            Calificacion.objects.create(
                colegio=self.colegio,
                evaluacion=evaluacion,
                estudiante=est,
                nota=nota,
                registrado_por=self.user_profesor
            )
        
        # Calcular promedio
        from django.db.models import Avg
        promedio = Calificacion.objects.filter(
            evaluacion=evaluacion
        ).aggregate(promedio=Avg('nota'))['promedio']
        
        self.assertIsNotNone(promedio)
        self.assertAlmostEqual(float(promedio), 6.0, places=1)
    
    def test_admin_puede_contar_clases_activas(self):
        """Verificar que un administrador puede contar las clases activas"""
        # Crear varias clases
        for i in range(4):
            asig = Asignatura.objects.create(
                colegio=self.colegio,
                nombre=f"Asignatura Count {i}",
                codigo=f"ACT{i}",
                horas_semanales=3,
                activa=True
            )
            
            Clase.objects.create(
                colegio=self.colegio,
                curso=self.curso,
                asignatura=asig,
                profesor=self.user_profesor,
                activo=True
            )
        
        # Contar clases activas
        clases_activas = Clase.objects.filter(
            colegio=self.colegio,
            activo=True
        ).count()
        
        self.assertGreaterEqual(clases_activas, 5)  # self.clase + 4 nuevas
    
    def test_admin_puede_listar_estudiantes_sin_notas(self):
        """Verificar que un administrador puede listar estudiantes sin calificaciones"""
        # Crear evaluación
        evaluacion = Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Pendiente",
            fecha_evaluacion=date.today(),
            ponderacion=Decimal('50.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        # Crear estudiantes (algunos con notas, otros sin)
        est_con_nota, _ = self.crear_usuario_estudiante(
            email="est_con_nota@test.cl",
            rut="60606061-1"
        )
        
        est_sin_nota, _ = self.crear_usuario_estudiante(
            email="est_sin_nota@test.cl",
            rut="60606062-2"
        )
        
        # Solo agregar nota a uno
        Calificacion.objects.create(
            colegio=self.colegio,
            evaluacion=evaluacion,
            estudiante=est_con_nota,
            nota=Decimal('6.0'),
            registrado_por=self.user_profesor
        )
        
        # Listar estudiantes sin nota en esta evaluación
        from backend.apps.accounts.models import PerfilEstudiante
        estudiantes_curso = User.objects.filter(
            perfil_estudiante__curso_actual_id=self.curso.id_curso
        )
        
        estudiantes_con_nota = Calificacion.objects.filter(
            evaluacion=evaluacion
        ).values_list('estudiante_id', flat=True)
        
        estudiantes_sin_nota = estudiantes_curso.exclude(
            id__in=estudiantes_con_nota
        )
        
        self.assertGreaterEqual(estudiantes_sin_nota.count(), 1)
        self.assertIn(est_sin_nota, estudiantes_sin_nota)
    
    def test_admin_puede_generar_reporte_evaluaciones_pendientes(self):
        """Verificar que un administrador puede listar evaluaciones pendientes"""
        # Crear evaluaciones futuras
        from datetime import timedelta
        
        Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Futura 1",
            fecha_evaluacion=date.today() + timedelta(days=7),
            ponderacion=Decimal('30.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        Evaluacion.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            nombre="Prueba Futura 2",
            fecha_evaluacion=date.today() + timedelta(days=14),
            ponderacion=Decimal('30.00'),
            tipo_evaluacion='sumativa',
            activa=True
        )
        
        # Listar evaluaciones futuras
        evaluaciones_pendientes = Evaluacion.objects.filter(
            colegio=self.colegio,
            fecha_evaluacion__gt=date.today(),
            activa=True
        )
        
        self.assertGreaterEqual(evaluaciones_pendientes.count(), 2)
    
    def test_admin_puede_contar_asignaturas_activas(self):
        """Verificar que un administrador puede contar asignaturas activas"""
        # Crear asignaturas
        for i in range(5):
            Asignatura.objects.create(
                colegio=self.colegio,
                nombre=f"Asignatura Activa {i}",
                codigo=f"AAC{i}",
                horas_semanales=3,
                activa=True
            )
        
        # Contar asignaturas activas
        asignaturas_activas = Asignatura.objects.filter(
            colegio=self.colegio,
            activa=True
        ).count()
        
        self.assertGreaterEqual(asignaturas_activas, 6)  # self.asignatura + 5 nuevas
    
    def test_admin_puede_calcular_porcentaje_asistencia_general(self):
        """Verificar que un administrador puede calcular porcentaje de asistencia general"""
        # Crear estudiantes
        estudiantes = []
        for i in range(4):
            est, _ = self.crear_usuario_estudiante(
                email=f"est_porc{i}@test.cl",
                rut=f"7070707{i}-{i}"
            )
            estudiantes.append(est)
        
        # Registrar asistencia (3 presentes, 1 ausente)
        for i, est in enumerate(estudiantes):
            Asistencia.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                estudiante=est,
                fecha=date.today(),
                estado='P' if i < 3 else 'A',
                tipo_asistencia='Presencial'
            )
        
        # Calcular porcentaje
        total = Asistencia.objects.filter(
            colegio=self.colegio,
            fecha=date.today()
        ).count()
        
        presentes = Asistencia.objects.filter(
            colegio=self.colegio,
            fecha=date.today(),
            estado='P'
        ).count()
        
        porcentaje = (presentes / total) * 100 if total > 0 else 0
        
        self.assertEqual(total, 4)
        self.assertEqual(presentes, 3)
        self.assertEqual(porcentaje, 75.0)
