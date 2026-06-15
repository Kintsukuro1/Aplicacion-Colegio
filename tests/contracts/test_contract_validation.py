"""
Tests de Validación de Contratos - Fase 6

Este módulo valida que todos los services críticos cumplan con los contratos
definidos en SYSTEM_CONTRACTS.md.

Propósito:
- Prevenir violaciones de contratos durante desarrollo
- Garantizar consistencia de respuestas
- Validar estructura de ErrorResponseBuilder
- Asegurar inmutabilidad de contratos

Ejecutar:
    pytest tests/contracts/test_contract_validation.py -v
"""

import pytest
from django.test import TestCase
from backend.apps.accounts.services.auth_service import AuthService
from backend.apps.core.services.data_repair_service import DataRepairService
from backend.apps.core.services.system_health_service import SystemHealthService
from backend.apps.core.services.setup_service import SetupService
from backend.common.utils.error_response import ErrorResponseBuilder, ERROR_MESSAGES
from backend.apps.accounts.models import Role, User
from backend.apps.institucion.models import (
    Colegio, Region, Comuna, CicloAcademico, 
    TipoEstablecimiento, DependenciaAdministrativa
)
from django.utils import timezone
from datetime import date, timedelta


# ============================================================================
# CONTRATOS BASE - Validadores Reutilizables
# ============================================================================

class ContractValidators:
    """Validadores de estructura de contratos"""
    
    @staticmethod
    def validate_query_operation_success(result):
        """Valida estructura de Query Operation exitosa"""
        assert isinstance(result, dict), "Query Operation debe retornar dict"
        assert 'success' in result, "Query Operation debe tener 'success'"
        assert 'data' in result, "Query Operation debe tener 'data'"
        assert isinstance(result['success'], bool), "'success' debe ser bool"
        assert result['success'] is True, "Query exitosa debe tener success=True"
        assert result['data'] is not None, "Query exitosa debe tener data no None"
    
    @staticmethod
    def validate_query_operation_failure(result):
        """Valida estructura de Query Operation fallida"""
        assert isinstance(result, dict), "Query Operation debe retornar dict"
        assert 'success' in result, "Query Operation debe tener 'success'"
        assert 'data' in result, "Query Operation debe tener 'data'"
        assert 'error' in result, "Query fallida debe tener 'error'"
        assert isinstance(result['success'], bool), "'success' debe ser bool"
        assert result['success'] is False, "Query fallida debe tener success=False"
        
        # Validar que error es ErrorResponseBuilder
        error = result['error']
        assert isinstance(error, dict), "'error' debe ser dict"
        assert 'error_type' in error, "Error debe tener 'error_type'"
        assert 'user_message' in error, "Error debe tener 'user_message'"
        assert 'action_url' in error, "Error debe tener 'action_url'"
        assert 'context' in error, "Error debe tener 'context'"
    
    @staticmethod
    def validate_command_operation_success(result):
        """Valida estructura de Command Operation exitosa"""
        assert isinstance(result, dict), "Command Operation debe retornar dict"
        assert 'success' in result, "Command Operation debe tener 'success'"
        assert 'message' in result, "Command Operation debe tener 'message'"
        assert isinstance(result['success'], bool), "'success' debe ser bool"
        assert isinstance(result['message'], str), "'message' debe ser str"
        assert result['success'] is True, "Command exitoso debe tener success=True"
        assert len(result['message']) > 0, "'message' no debe estar vacío"
    
    @staticmethod
    def validate_command_operation_failure(result):
        """Valida estructura de Command Operation fallida"""
        assert isinstance(result, dict), "Command Operation debe retornar dict"
        assert 'success' in result, "Command Operation debe tener 'success'"
        assert 'message' in result or 'error' in result, "Command fallido debe tener 'message' o 'error'"
        assert result['success'] is False, "Command fallido debe tener success=False"
    
    @staticmethod
    def validate_validation_operation(result):
        """Valida estructura de Validation Operation"""
        assert result is None or isinstance(result, dict), \
            "Validation Operation debe retornar None o Dict"
        
        if result is not None:
            # Debe ser ErrorResponseBuilder dict
            assert 'error_type' in result, "Validation error debe tener 'error_type'"
            assert 'user_message' in result, "Validation error debe tener 'user_message'"
            assert 'action_url' in result, "Validation error debe tener 'action_url'"
            assert 'context' in result, "Validation error debe tener 'context'"
    
    @staticmethod
    def validate_auth_operation_success(result):
        """Valida estructura de Auth Operation exitosa"""
        assert isinstance(result, dict), "Auth Operation debe retornar dict"
        assert 'success' in result, "Auth Operation debe tener 'success'"
        assert 'user' in result, "Auth Operation debe tener 'user'"
        assert result['success'] is True, "Auth exitoso debe tener success=True"
        assert result['user'] is not None, "Auth exitoso debe tener user no None"
        assert hasattr(result['user'], 'email'), "user debe ser User object"
    
    @staticmethod
    def validate_auth_operation_failure(result):
        """Valida estructura de Auth Operation fallida"""
        assert isinstance(result, dict), "Auth Operation debe retornar dict"
        assert 'success' in result, "Auth Operation debe tener 'success'"
        assert 'user' in result, "Auth Operation debe tener 'user'"
        assert 'error' in result, "Auth fallido debe tener 'error'"
        assert result['success'] is False, "Auth fallido debe tener success=False"
        assert result['user'] is None, "Auth fallido debe tener user=None"


# ============================================================================
# TEST: ErrorResponseBuilder Contract
# ============================================================================

class TestErrorResponseBuilderContract(TestCase):
    """Valida que ErrorResponseBuilder cumpla contrato inmutable"""
    
    def test_error_builder_structure(self):
        """ErrorResponseBuilder.build() debe retornar estructura correcta"""
        error = ErrorResponseBuilder.build('MISSING_CICLO_ACTIVO')
        
        # Validar campos obligatorios
        assert 'error_type' in error
        assert 'user_message' in error
        assert 'action_url' in error
        assert 'context' in error
        
        # Validar tipos
        assert isinstance(error['error_type'], str)
        assert isinstance(error['user_message'], str)
        assert isinstance(error['action_url'], str)
        assert isinstance(error['context'], dict)
    
    def test_all_error_types_defined(self):
        """Todos los error_types usados deben estar en ERROR_MESSAGES"""
        # Lista de error types que DEBEN existir (contrato congelado)
        required_error_types = [
            'MISSING_CICLO_ACTIVO',
            'MISSING_COURSES',
            'PERMISSION_DENIED',
            'INVALID_STATE',
            'DATA_INCONSISTENCY',
            'INVALID_RELATIONSHIP',
            'VALIDATION_ERROR',
            'AUTHENTICATION_FAILED'
        ]
        
        for error_type in required_error_types:
            assert error_type in ERROR_MESSAGES, \
                f"Error type '{error_type}' debe estar definido en ERROR_MESSAGES"
    
    def test_error_builder_with_context(self):
        """ErrorResponseBuilder debe manejar context correctamente"""
        context = {'user_id': 123, 'action': 'login'}
        error = ErrorResponseBuilder.build('PERMISSION_DENIED', context=context)
        
        assert error['context'] == context
        assert error['context']['user_id'] == 123


# ============================================================================
# TEST: AuthService Contracts
# ============================================================================

@pytest.mark.django_db
class TestAuthServiceContracts(TestCase):
    """Valida contratos de AuthService"""
    
    def setUp(self):
        """Setup común para tests de AuthService"""
        # Crear rol
        self.role_profesor = Role.objects.create(nombre='Profesor')
        
        # Crear usuario de prueba
        self.user = User.objects.create(
            email='test@colegio.cl',
            nombre='Test',
            apellido_paterno='User',
            role=self.role_profesor,
            is_active=True
        )
        self.user.set_password('TestPassword123!')
        self.user.save()
    
    def test_validate_role_for_login_type_contract(self):
        """AuthService.validate_role_for_login_type debe cumplir contrato de Validation Operation"""
        # Test con rol válido - debe retornar None
        result = AuthService.validate_role_for_login_type(self.user, 'staff')
        ContractValidators.validate_validation_operation(result)
        assert result is None, "Profesor debe poder acceder a portal staff"
        
        # Test con rol inválido - debe retornar ErrorResponseBuilder dict
        result = AuthService.validate_role_for_login_type(self.user, 'student')
        ContractValidators.validate_validation_operation(result)
        assert result is not None, "Profesor no debe poder acceder a portal student"
        assert result['error_type'] == 'PERMISSION_DENIED'


# ============================================================================
# TEST: DataRepairService Contracts
# ============================================================================

@pytest.mark.django_db
class TestDataRepairServiceContracts(TestCase):
    """Valida contratos de DataRepairService"""
    
    def setUp(self):
        """Setup común para tests de DataRepairService"""
        # Crear región, comuna
        self.region = Region.objects.create(nombre='Región Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        
        # Crear tipo establecimiento y dependencia
        self.tipo_establecimiento = TipoEstablecimiento.objects.create(nombre='Colegio')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Crear colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='76123456-7',
            nombre='Colegio Test',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        
        # Crear admin user para audit trail
        self.admin = User.objects.create(
            email='admin@colegio.cl',
            nombre='Admin',
            apellido_paterno='Test',
            is_active=True,
            is_staff=True,
            is_superuser=True
        )
    
    def test_repair_all_contract(self):
        """DataRepairService.repair_all() debe cumplir su contrato específico"""
        service = DataRepairService()
        result = service.repair_all(self.colegio.rbd, dry_run=True)
        
        # Validar estructura específica de DataRepairService
        assert isinstance(result, dict)
        assert 'timestamp' in result
        assert 'total_corrections' in result
        assert 'categories' in result
        assert 'dry_run' in result
        
        # Validar tipos
        assert isinstance(result['timestamp'], str)
        assert isinstance(result['total_corrections'], int)
        assert isinstance(result['dry_run'], bool)
        assert result['dry_run'] == True  # Porque pasamos dry_run=True
        
        # Validar categorías
        categories = result['categories']
        expected_categories = ['matriculas', 'cursos', 'clases', 'usuarios', 'perfiles_estudiante']
        for category_name in expected_categories:
            assert category_name in categories, f"Debe existir categoría {category_name}"
            category_data = categories[category_name]
            assert 'count' in category_data, f"Categoría {category_name} debe tener 'count'"
            assert 'corrections' in category_data, f"Categoría {category_name} debe tener 'corrections'"
            assert isinstance(category_data['count'], int)
            assert isinstance(category_data['corrections'], list)


# ============================================================================
# TEST: SystemHealthService Contracts
# ============================================================================

@pytest.mark.django_db
class TestSystemHealthServiceContracts(TestCase):
    """Valida contratos de SystemHealthService"""
    
    def setUp(self):
        """Setup común para tests de SystemHealthService"""
        # Crear región, comuna
        self.region = Region.objects.create(nombre='Región Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        
        # Crear tipo establecimiento y dependencia
        self.tipo_establecimiento = TipoEstablecimiento.objects.create(nombre='Colegio')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Crear colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='76123457-5',
            nombre='Colegio Test',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
        
        # Crear admin user
        self.admin = User.objects.create(
            email='admin@colegio.cl',
            nombre='Admin',
            apellido_paterno='Test',
            is_active=True,
            is_staff=True,
            is_superuser=True
        )
        
        # Crear ciclo académico para evitar warnings
        CicloAcademico.objects.create(
            colegio=self.colegio,
            nombre='2026',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=365),
            estado='ACTIVO',
            creado_por=self.admin,
            modificado_por=self.admin
        )
    
    def test_get_system_health_contract(self):
        """SystemHealthService.get_system_health() debe cumplir su contrato específico"""
        result = SystemHealthService.get_system_health(self.colegio.rbd)
        
        # Validar estructura específica (SystemHealthService tiene su propia estructura)
        assert isinstance(result, dict)
        assert 'is_healthy' in result
        assert 'timestamp' in result
        assert 'colegio' in result
        assert 'summary' in result
        assert 'data_integrity' in result
        assert 'critical_issues' in result
        assert 'warnings' in result
        
        # Validar summary
        summary = result['summary']
        assert 'total_issues' in summary
        assert 'critical_issues' in summary
        assert 'warnings' in summary
        assert isinstance(summary['total_issues'], int)
        assert isinstance(summary['critical_issues'], int)
        assert isinstance(summary['warnings'], int)
        
        # Validar data_integrity
        assert 'has_inconsistencies' in result['data_integrity']
        assert 'categories' in result['data_integrity']
        assert isinstance(result['data_integrity']['has_inconsistencies'], bool)
        
        # Validar listas
        assert isinstance(result['critical_issues'], list)
        assert isinstance(result['warnings'], list)


# ============================================================================
# TEST: SetupService Contracts
# ============================================================================

@pytest.mark.django_db
class TestSetupServiceContracts(TestCase):
    """Valida contratos de SetupService"""
    
    def setUp(self):
        """Setup común para tests de SetupService"""
        # Crear región, comuna
        self.region = Region.objects.create(nombre='Región Metropolitana')
        self.comuna = Comuna.objects.create(nombre='Santiago', region=self.region)
        
        # Crear tipo establecimiento y dependencia
        self.tipo_establecimiento = TipoEstablecimiento.objects.create(nombre='Colegio')
        self.dependencia = DependenciaAdministrativa.objects.create(nombre='Municipal')
        
        # Crear colegio
        self.colegio = Colegio.objects.create(
            rbd=12345,
            rut_establecimiento='76123458-3',
            nombre='Colegio Test',
            comuna=self.comuna,
            tipo_establecimiento=self.tipo_establecimiento,
            dependencia=self.dependencia
        )
    
    def test_get_setup_status_contract(self):
        """SetupService.get_setup_status() debe cumplir su contrato específico"""
        result = SetupService.get_setup_status(self.colegio.rbd)
        
        # Validar estructura específica (SetupService tiene su propia estructura)
        assert isinstance(result, dict)
        assert 'setup_complete' in result
        assert 'missing_steps' in result
        assert 'next_required_step' in result
        assert 'total_steps' in result
        assert 'completed_steps' in result
        
        # Validar tipos
        assert isinstance(result['setup_complete'], bool)
        assert isinstance(result['missing_steps'], list)
        assert isinstance(result['total_steps'], int)
        assert isinstance(result['completed_steps'], int)
        assert result['next_required_step'] is None or isinstance(result['next_required_step'], int)
        
        # Validar valores
        assert result['total_steps'] > 0
        assert result['completed_steps'] >= 0
        assert result['completed_steps'] <= result['total_steps']


# ============================================================================
# TEST: Contract Immutability
# ============================================================================

class TestContractImmutability(TestCase):
    """Valida que contratos sean inmutables"""
    
    def test_error_types_are_frozen(self):
        """Error types definidos no deben cambiar"""
        # Lista congelada de error types (Fase 6)
        frozen_error_types = {
            'MISSING_CICLO_ACTIVO',
            'MISSING_COURSES',
            'MISSING_TEACHERS_ASSIGNED',
            'MISSING_STUDENTS_ENROLLED',
            'INVALID_PREREQUISITE',
            'INVALID_CURSO_STATE',
            'INVALID_MATRICULA_STATE',
            'PERMISSION_DENIED',
            'SCHOOL_NOT_CONFIGURED',
            'DATA_INCONSISTENCY',
            'INVALID_RELATIONSHIP',
            'ORPHANED_ENTITY',
            'STATE_MISMATCH',
            'INVALID_STATE'
        }
        
        # Todos los frozen types DEBEN existir
        for error_type in frozen_error_types:
            assert error_type in ERROR_MESSAGES, \
                f"CONTRATO ROTO: Error type '{error_type}' fue eliminado"
    
    def test_error_message_structure_immutable(self):
        """Estructura de ErrorResponseBuilder no puede cambiar"""
        error = ErrorResponseBuilder.build('PERMISSION_DENIED')
        
        # Campos obligatorios congelados
        required_fields = {'error_type', 'user_message', 'action_url', 'context'}
        actual_fields = set(error.keys())
        
        assert required_fields == actual_fields, \
            f"CONTRATO ROTO: Estructura de error cambió. " \
            f"Esperado: {required_fields}, Actual: {actual_fields}"


# ============================================================================
# Ejecución
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
