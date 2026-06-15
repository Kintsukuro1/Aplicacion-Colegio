"""
Tests de gestión de materiales de clase para profesores
"""
from tests.common.test_base import BaseTestCase
from backend.apps.cursos.models import Clase, Asignatura
from backend.apps.academico.models import MaterialClase
from django.core.files.uploadedfile import SimpleUploadedFile


class ProfesorMaterialesTest(BaseTestCase):
    """Tests de funcionalidad de materiales del profesor"""
    
    def setUp(self):
        super().setUp()
        self.user_profesor = self.crear_usuario_profesor()
        
        # Crear asignatura y clase
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
    
    def test_profesor_puede_subir_material(self):
        """Verificar que un profesor puede subir material de clase"""
        # Crear archivo de prueba
        archivo = SimpleUploadedFile(
            "documento_test.pdf",
            b"contenido del archivo",
            content_type="application/pdf"
        )
        
        material = MaterialClase.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            titulo="Guía de Ejercicios",
            descripcion="Ejercicios de álgebra",
            archivo=archivo,
            tipo_archivo='documento',
            es_publico=True,
            tamanio_bytes=1024,
            subido_por=self.user_profesor,
            activo=True
        )
        
        self.assertIsNotNone(material.id_material)
        self.assertEqual(material.titulo, "Guía de Ejercicios")
        self.assertEqual(material.subido_por, self.user_profesor)
    
    def test_material_tiene_tipos_validos(self):
        """Verificar que los materiales tienen tipos válidos"""
        tipos_validos = ['documento', 'presentacion', 'video', 'audio', 'imagen', 'otro']
        
        archivo = SimpleUploadedFile("test.pdf", b"contenido")
        
        material = MaterialClase.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            titulo="Material Test",
            archivo=archivo,
            tipo_archivo='presentacion',
            subido_por=self.user_profesor
        )
        
        self.assertIn(material.tipo_archivo, tipos_validos)
    
    def test_material_puede_ser_publico_o_privado(self):
        """Verificar que los materiales pueden ser públicos o privados"""
        archivo1 = SimpleUploadedFile("publico.pdf", b"contenido")
        archivo2 = SimpleUploadedFile("privado.pdf", b"contenido")
        
        # Material público
        material_publico = MaterialClase.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            titulo="Material Público",
            archivo=archivo1,
            es_publico=True,
            subido_por=self.user_profesor
        )
        
        # Material privado
        material_privado = MaterialClase.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            titulo="Material Privado",
            archivo=archivo2,
            es_publico=False,
            subido_por=self.user_profesor
        )
        
        self.assertTrue(material_publico.es_publico)
        self.assertFalse(material_privado.es_publico)
    
    def test_material_tiene_tamanio(self):
        """Verificar que se registra el tamaño del material"""
        archivo = SimpleUploadedFile("archivo.pdf", b"x" * 2048)
        
        material = MaterialClase.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            titulo="Archivo con tamaño",
            archivo=archivo,
            tamanio_bytes=2048,
            subido_por=self.user_profesor
        )
        
        self.assertEqual(material.tamanio_bytes, 2048)
    
    def test_profesor_puede_consultar_sus_materiales(self):
        """Verificar que un profesor puede consultar sus materiales subidos"""
        # Subir varios materiales
        for i in range(3):
            archivo = SimpleUploadedFile(f"archivo{i}.pdf", b"contenido")
            MaterialClase.objects.create(
                colegio=self.colegio,
                clase=self.clase,
                titulo=f"Material {i}",
                archivo=archivo,
                subido_por=self.user_profesor
            )
        
        materiales = MaterialClase.objects.filter(subido_por=self.user_profesor)
        self.assertEqual(materiales.count(), 3)
    
    def test_material_desactivado_no_aparece(self):
        """Verificar que materiales desactivados se filtran correctamente"""
        archivo = SimpleUploadedFile("test.pdf", b"contenido")
        
        material = MaterialClase.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            titulo="Material Desactivado",
            archivo=archivo,
            subido_por=self.user_profesor,
            activo=False
        )
        
        materiales_activos = MaterialClase.objects.filter(
            subido_por=self.user_profesor,
            activo=True
        )
        
        self.assertEqual(materiales_activos.count(), 0)
    
    def test_material_puede_tener_descripcion(self):
        """Verificar que los materiales pueden tener descripción"""
        archivo = SimpleUploadedFile("guia.pdf", b"contenido")
        
        material = MaterialClase.objects.create(
            colegio=self.colegio,
            clase=self.clase,
            titulo="Guía Completa",
            descripcion="Esta guía cubre todos los temas del semestre",
            archivo=archivo,
            subido_por=self.user_profesor
        )
        
        self.assertIsNotNone(material.descripcion)
        self.assertIn("todos los temas", material.descripcion)
