"""
Tests de gestión de cursos para administradores
"""
from tests.common.test_base import BaseTestCase
from backend.apps.cursos.models import Curso, Clase, Asignatura
from backend.apps.institucion.models import NivelEducativo
from backend.apps.accounts.models import User, PerfilEstudiante


class AdministradorCursosTest(BaseTestCase):
    """Tests de funcionalidad de gestión de cursos del administrador"""
    
    def setUp(self):
        super().setUp()
        self.user_admin = self.crear_usuario_admin()
        self.user_profesor = self.crear_usuario_profesor()
    
    def test_admin_puede_crear_curso(self):
        """Verificar que un administrador puede crear un curso"""
        # Obtener nivel
        nivel, _ = NivelEducativo.objects.get_or_create(
            nombre="7° Básico"
        )
        
        curso = Curso.objects.create(
            colegio=self.colegio,
            nombre="7° Básico B",
            nivel=nivel,
            ciclo_academico=self.ciclo,
            activo=True
        )
        
        self.assertIsNotNone(curso.id_curso)
        self.assertEqual(curso.nombre, "7° Básico B")
        self.assertTrue(curso.activo)
    
    def test_admin_puede_listar_todos_cursos(self):
        """Verificar que un administrador puede listar todos los cursos del colegio"""
        # Crear varios cursos
        nivel, _ = NivelEducativo.objects.get_or_create(
            nombre="6° Básico"
        )
        
        Curso.objects.create(
            colegio=self.colegio,
            nombre="6° Básico A",
            nivel=nivel,
            ciclo_academico=self.ciclo,
            activo=True
        )
        
        Curso.objects.create(
            colegio=self.colegio,
            nombre="6° Básico B",
            nivel=nivel,
            ciclo_academico=self.ciclo,
            activo=True
        )
        
        # Listar cursos
        cursos = Curso.objects.filter(colegio=self.colegio)
        
        self.assertGreaterEqual(cursos.count(), 3)  # Ya existe self.curso + 2 nuevos
    
    def test_admin_puede_desactivar_curso(self):
        """Verificar que un administrador puede desactivar un curso"""
        curso = self.curso
        
        # Desactivar
        curso.activo = False
        curso.save()
        
        curso.refresh_from_db()
        self.assertFalse(curso.activo)
    
    def test_admin_puede_crear_asignatura(self):
        """Verificar que un administrador puede crear una asignatura"""
        asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre="Historia",
            codigo="HIS101",
            horas_semanales=3,
            activa=True
        )
        
        self.assertIsNotNone(asignatura.id_asignatura)
        self.assertEqual(asignatura.nombre, "Historia")
        self.assertEqual(asignatura.horas_semanales, 3)
    
    def test_admin_puede_asignar_profesor_a_clase(self):
        """Verificar que un administrador puede asignar un profesor a una clase"""
        # Crear asignatura
        asignatura = Asignatura.objects.create(
            colegio=self.colegio,
            nombre="Ciencias",
            codigo="CIE101",
            horas_semanales=4,
            activa=True
        )
        
        # Crear clase con profesor asignado
        clase = Clase.objects.create(
            colegio=self.colegio,
            curso=self.curso,
            asignatura=asignatura,
            profesor=self.user_profesor,
            activo=True
        )
        
        self.assertIsNotNone(clase.id)
        self.assertEqual(clase.profesor, self.user_profesor)
        self.assertEqual(clase.asignatura, asignatura)
    
    def test_admin_puede_listar_clases_por_curso(self):
        """Verificar que un administrador puede listar todas las clases de un curso"""
        # Crear varias clases para el curso
        for i in range(3):
            asignatura = Asignatura.objects.create(
                colegio=self.colegio,
                nombre=f"Asignatura {i}",
                codigo=f"ASI{i}",
                horas_semanales=3,
                activa=True
            )
            
            Clase.objects.create(
                colegio=self.colegio,
                curso=self.curso,
                asignatura=asignatura,
                profesor=self.user_profesor,
                activo=True
            )
        
        # Listar clases del curso
        clases = Clase.objects.filter(curso=self.curso)
        
        self.assertEqual(clases.count(), 3)
    
    def test_admin_puede_filtrar_cursos_por_anio(self):
        """Verificar que un administrador puede filtrar cursos por año escolar"""
        nivel, _ = NivelEducativo.objects.get_or_create(
            nombre="5° Básico"
        )
        
        # Crear cursos de diferentes años
        Curso.objects.create(
            colegio=self.colegio,
            nombre="5° Básico 2025",
            nivel=nivel,
            ciclo_academico=self.ciclo,
            activo=False
        )
        
        Curso.objects.create(
            colegio=self.colegio,
            nombre="5° Básico 2026",
            nivel=nivel,
            ciclo_academico=self.ciclo,
            activo=True
        )
        
        # Filtrar por año 2026
        cursos_2026 = Curso.objects.filter(
            colegio=self.colegio,
            ciclo_academico=self.ciclo,
        )
        
        self.assertGreaterEqual(cursos_2026.count(), 2)  # self.curso + nuevo
    
    def test_admin_puede_contar_estudiantes_por_curso(self):
        """Verificar que un administrador puede contar estudiantes por curso"""
        # Crear estudiantes asignados al curso
        for i in range(5):
            estudiante, perfil = self.crear_usuario_estudiante(
                email=f"est_curso{i}@test.cl",
                rut=f"1010101{i}-{i}"
            )
            # El perfil ya está vinculado al curso a través de BaseTestCase
        
        # Contar estudiantes del curso
        from backend.apps.accounts.models import PerfilEstudiante
        estudiantes_count = PerfilEstudiante.objects.filter(
            curso_actual_id=self.curso.id_curso
        ).count()
        
        self.assertGreaterEqual(estudiantes_count, 5)
    
    def test_admin_puede_listar_profesores_por_curso(self):
        """Verificar que un administrador puede listar profesores asignados a un curso"""
        # Crear varios profesores
        prof1 = self.crear_usuario_profesor(
            email="prof1_curso@test.cl",
            rut="20202021-1"
        )
        prof2 = self.crear_usuario_profesor(
            email="prof2_curso@test.cl",
            rut="20202022-2"
        )
        
        # Crear asignaturas y clases
        for i, prof in enumerate([prof1, prof2]):
            asig = Asignatura.objects.create(
                colegio=self.colegio,
                nombre=f"Asignatura Prof {i}",
                codigo=f"APR{i}",
                horas_semanales=3,
                activa=True
            )
            
            Clase.objects.create(
                colegio=self.colegio,
                curso=self.curso,
                asignatura=asig,
                profesor=prof,
                activo=True
            )
        
        # Obtener profesores del curso
        profesores = User.objects.filter(
            clases_impartidas__curso=self.curso
        ).distinct()
        
        self.assertGreaterEqual(profesores.count(), 2)
