"""
Tests de autenticación y permisos básicos para asesor financiero
"""
from tests.common.test_base import BaseTestCase
from backend.apps.accounts.models import User, PerfilAsesorFinanciero


class AsesorFinancieroAuthTest(BaseTestCase):
    """Tests de autenticación básica del asesor financiero"""
    
    def test_asesor_puede_ser_creado(self):
        """Verificar que un asesor financiero puede ser creado"""
        asesor = User.objects.create_user(
            email="asesor.test@colegio.cl",
            rut="40404040-4",
            nombre="Pedro",
            apellido_paterno="Soto",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
        )
        
        self.assertIsNotNone(asesor)
        self.assertEqual(asesor.email, "asesor.test@colegio.cl")
        self.assertEqual(asesor.rut, "40404040-4")
    
    def test_asesor_tiene_rol_correcto(self):
        """Verificar que el asesor tiene el rol correcto"""
        asesor = User.objects.create_user(
            email="asesor2@colegio.cl",
            rut="40404041-2",
            nombre="María",
            apellido_paterno="González",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
        )
        
        self.assertEqual(asesor.role.nombre, "Asesor financiero")
    
    def test_asesor_puede_tener_perfil(self):
        """Verificar que se puede crear un perfil de asesor financiero"""
        asesor = User.objects.create_user(
            email="asesor3@colegio.cl",
            rut="40404042-0",
            nombre="Juan",
            apellido_paterno="Ramírez",
            role=self.role_asesor,
            rbd_colegio=self.colegio.rbd
        )
        
        # Crear perfil de asesor financiero
        perfil = PerfilAsesorFinanciero.objects.create(
            user=asesor,
            area_especialidad='finanzas',
            titulo_profesional='Contador Auditor',
            puede_aprobar_descuentos=True,
            puede_anular_pagos=False,
            puede_modificar_aranceles=True,
            puede_generar_reportes_contables=True,
            acceso_configuracion_transbank=False,
            estado_laboral='Activo'
        )
        
        self.assertIsNotNone(perfil)
        self.assertEqual(perfil.user, asesor)
        self.assertTrue(perfil.puede_aprobar_descuentos)
        self.assertFalse(perfil.puede_anular_pagos)
        self.assertEqual(perfil.estado_laboral, 'Activo')
