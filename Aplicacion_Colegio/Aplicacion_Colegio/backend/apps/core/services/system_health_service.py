"""
Servicio de monitoreo de salud del sistema.

Este servicio proporciona una visión completa del estado de salud del sistema,
combinando validaciones de integridad de datos y estado de configuración.

Responsabilidades:
- Detectar inconsistencias de datos
- Verificar estado de setup del colegio
- Identificar problemas críticos que requieren atención inmediata
- Retornar estado estructurado para monitoreo

Filosofía:
- NUNCA modifica datos (solo consulta)
- NUNCA lanza excepciones (retorna estado)
- Puede ser invocado desde endpoint de health check
- Reutiliza lógica de audit_data_integrity y setup_service
"""
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Q
from backend.apps.matriculas.models import Matricula
from backend.apps.cursos.models import Curso, Clase
from backend.apps.accounts.models import User, PerfilEstudiante
from backend.apps.institucion.models import Colegio, CicloAcademico
from backend.apps.core.services.setup_service import SetupService


class SystemHealthService:
    """
    Servicio para monitorear la salud del sistema.
    
    Combina:
    - Auditoría de integridad de datos
    - Estado de configuración (setup)
    - Detección de problemas críticos
    """

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        SystemHealthService.validate(operation, params)
        return SystemHealthService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(SystemHealthService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')
    
    @staticmethod
    def get_system_health(rbd_colegio=None):
        """
        Obtiene el estado de salud del sistema.
        
        Si se proporciona rbd_colegio, el análisis se limita a ese colegio.
        Si no, analiza todo el sistema.
        
        Args:
            rbd_colegio (str, optional): RBD del colegio a analizar
            
        Returns:
            dict con estructura:
            {
                'is_healthy': bool,
                'timestamp': str,
                'colegio': str or None,
                'summary': {
                    'total_issues': int,
                    'critical_issues': int,
                    'warnings': int
                },
                'setup_status': dict,  # Si rbd_colegio proporcionado
                'data_integrity': {
                    'has_inconsistencies': bool,
                    'categories': dict
                },
                'critical_issues': list,
                'warnings': list
            }
        """
        # Validar que el colegio existe si se proporciona
        if rbd_colegio:
            try:
                colegio = Colegio.objects.get(rbd=rbd_colegio)
            except Colegio.DoesNotExist:
                return {
                    'is_healthy': False,
                    'timestamp': datetime.now().isoformat(),
                    'colegio': rbd_colegio,
                    'error': 'COLEGIO_NOT_FOUND',
                    'error_message': f'Colegio con RBD {rbd_colegio} no encontrado',
                    'summary': {
                        'total_issues': 1,
                        'critical_issues': 1,
                        'warnings': 0
                    }
                }
        
        # 1. Healthchecks de infraestructura (db, redis, migrations)
        infrastructure = SystemHealthService._check_infrastructure_health()

        # 2. Obtener estado de setup (si se especifica colegio)
        setup_status = None
        if rbd_colegio:
            setup_status = SetupService.get_setup_status(rbd_colegio)
        
        # 3. Auditar integridad de datos
        data_integrity = SystemHealthService._audit_data_integrity(rbd_colegio)
        
        # 4. Identificar problemas críticos y warnings
        critical_issues = []
        warnings = []

        # Problemas críticos de infraestructura
        for component_name, component_status in infrastructure.items():
            if not component_status.get('ok', False):
                critical_issues.append({
                    'type': f'INFRA_{component_name.upper()}_UNHEALTHY',
                    'category': 'infrastructure',
                    'description': component_status.get('detail', 'Componente no saludable'),
                    'severity': 'critical',
                    'action_required': f'Revisar componente {component_name} y recuperar operacion.',
                })
        
        # Problemas críticos de setup
        if setup_status:
            if not setup_status['setup_complete']:
                if 'MISSING_CICLO_ACTIVO' in setup_status['missing_steps']:
                    critical_issues.append({
                        'type': 'SETUP_MISSING_CICLO_ACTIVO',
                        'category': 'setup',
                        'description': 'El colegio no tiene un ciclo académico activo',
                        'severity': 'critical',
                        'action_required': 'Crear y activar un ciclo académico'
                    })
                
                # Otros pasos faltantes son warnings
                for step in setup_status['missing_steps']:
                    if step != 'MISSING_CICLO_ACTIVO':
                        warnings.append({
                            'type': f'SETUP_{step}',
                            'category': 'setup',
                            'description': f'Paso de setup faltante: {step}',
                            'severity': 'warning',
                            'action_required': 'Completar configuración inicial'
                        })
        
        # Problemas críticos de integridad de datos
        if data_integrity['has_inconsistencies']:
            for category_name, category_data in data_integrity['categories'].items():
                for issue in category_data['issues']:
                    # Determinar severidad basado en tipo
                    severity = SystemHealthService._determine_severity(issue['type'])
                    
                    issue_entry = {
                        'type': issue['type'],
                        'category': category_name,
                        'description': issue['description'],
                        'severity': severity,
                        'action_required': issue['suggested_action']
                    }
                    
                    if severity == 'critical':
                        critical_issues.append(issue_entry)
                    else:
                        warnings.append(issue_entry)
        
        # 5. Determinar salud general del sistema
        total_issues = len(critical_issues) + len(warnings)
        is_healthy = len(critical_issues) == 0 and len(warnings) == 0
        
        # 6. Construir respuesta
        response = {
            'is_healthy': is_healthy,
            'timestamp': datetime.now().isoformat(),
            'colegio': rbd_colegio,
            'infrastructure': infrastructure,
            'summary': {
                'total_issues': total_issues,
                'critical_issues': len(critical_issues),
                'warnings': len(warnings)
            },
            'data_integrity': data_integrity,
            'critical_issues': critical_issues,
            'warnings': warnings
        }
        
        # Agregar setup_status si se proporcionó colegio
        if setup_status:
            response['setup_status'] = setup_status
        
        return response

    @staticmethod
    def _check_infrastructure_health():
        """Valida componentes operativos base: db, redis y migraciones."""
        return {
            'db': SystemHealthService._check_database_health(),
            'redis': SystemHealthService._check_redis_health(),
            'migrations': SystemHealthService._check_migrations_health(),
        }

    @staticmethod
    def _check_database_health():
        try:
            conn = connections[DEFAULT_DB_ALIAS]
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            return {
                'ok': True,
                'detail': 'Database reachable',
            }
        except Exception as exc:
            return {
                'ok': False,
                'detail': f'Database check failed: {exc}',
            }

    @staticmethod
    def _check_redis_health():
        redis_url = getattr(settings, 'REDIS_URL', None)
        if not redis_url:
            return {
                'ok': True,
                'detail': 'Redis disabled in current environment',
            }

        probe_key = 'health:redis:probe'
        probe_value = datetime.now().isoformat()
        try:
            cache.set(probe_key, probe_value, timeout=10)
            recovered = cache.get(probe_key)
            cache.delete(probe_key)
            if recovered != probe_value:
                return {
                    'ok': False,
                    'detail': 'Redis reachable but read/write probe failed',
                }
            return {
                'ok': True,
                'detail': 'Redis reachable',
            }
        except Exception as exc:
            return {
                'ok': False,
                'detail': f'Redis check failed: {exc}',
            }

    @staticmethod
    def _check_migrations_health():
        try:
            conn = connections[DEFAULT_DB_ALIAS]
            executor = MigrationExecutor(conn)
            leaf_nodes = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(leaf_nodes)
            pending = len(plan)
            return {
                'ok': pending == 0,
                'pending_migrations': pending,
                'detail': 'No pending migrations' if pending == 0 else f'{pending} pending migrations',
            }
        except Exception as exc:
            return {
                'ok': False,
                'pending_migrations': None,
                'detail': f'Migration check failed: {exc}',
            }
    
    @staticmethod
    def check_data_consistency(rbd_colegio=None):
        """
        Verifica la consistencia de datos del sistema.
        
        Es una versión enfocada de get_system_health que solo retorna
        información de integridad de datos.
        
        Args:
            rbd_colegio (str, optional): RBD del colegio a analizar
            
        Returns:
            dict con estructura:
            {
                'has_inconsistencies': bool,
                'total_issues': int,
                'categories': dict
            }
        """
        return SystemHealthService._audit_data_integrity(rbd_colegio)
    
    @staticmethod
    def validate_setup_status(rbd_colegio):
        """
        Valida el estado de configuración de un colegio.
        
        Wrapper alrededor de SetupService.get_setup_status con
        interpretación adicional.
        
        Args:
            rbd_colegio (str): RBD del colegio
            
        Returns:
            dict con estructura:
            {
                'is_complete': bool,
                'is_ready_for_operation': bool,
                'setup_status': dict,
                'blockers': list
            }
        """
        setup_status = SetupService.get_setup_status(rbd_colegio)
        
        # Identificar bloqueadores
        blockers = []
        if 'MISSING_CICLO_ACTIVO' in setup_status.get('missing_steps', []):
            blockers.append({
                'step': 'MISSING_CICLO_ACTIVO',
                'description': 'Sin ciclo académico activo',
                'blocks_operation': True
            })
        
        # El colegio está listo para operar si tiene al menos ciclo activo
        has_ciclo_activo = 'MISSING_CICLO_ACTIVO' not in setup_status.get('missing_steps', [])
        
        return {
            'is_complete': setup_status['setup_complete'],
            'is_ready_for_operation': has_ciclo_activo,
            'setup_status': setup_status,
            'blockers': blockers
        }
    
    # ==================== MÉTODOS PRIVADOS ====================
    
    @staticmethod
    def _audit_data_integrity(rbd_colegio=None):
        """
        Audita la integridad de datos del sistema.
        
        Reutiliza la lógica del comando audit_data_integrity.
        
        Args:
            rbd_colegio (str, optional): Si se proporciona, filtra por colegio
            
        Returns:
            dict con categorías de problemas encontrados
        """
        categories = {}
        
        # Auditar cada categoría
        categories['matriculas_invalidas'] = SystemHealthService._audit_matriculas(rbd_colegio)
        categories['cursos_invalidos'] = SystemHealthService._audit_cursos(rbd_colegio)
        categories['clases_invalidas'] = SystemHealthService._audit_clases(rbd_colegio)
        categories['usuarios_huerfanos'] = SystemHealthService._audit_users(rbd_colegio)
        categories['perfiles_estudiante_invalidos'] = SystemHealthService._audit_perfil_estudiante(rbd_colegio)
        
        # Calcular total de problemas
        total_issues = sum(cat['count'] for cat in categories.values())
        
        return {
            'has_inconsistencies': total_issues > 0,
            'total_issues': total_issues,
            'categories': categories
        }
    
    @staticmethod
    def _audit_matriculas(rbd_colegio=None):
        """Auditar registros de Matrícula por relaciones inválidas"""
        issues = []
        
        # Base queryset
        base_qs = Matricula.objects.all()
        if rbd_colegio:
            base_qs = base_qs.filter(estudiante__rbd_colegio=rbd_colegio)
        
        # Check: Matrículas activas con curso inactivo
        matriculas_curso_inactivo = base_qs.filter(
            estado='ACTIVA',
            curso__activo=False
        ).select_related('curso', 'estudiante', 'ciclo_academico')
        
        for m in matriculas_curso_inactivo:
            issues.append({
                'id': m.id,
                'type': 'MATRICULA_CURSO_INACTIVO',
                'description': f'Matricula #{m.id} activa pero curso "{m.curso.nombre}" está inactivo',
                'suggested_action': 'Cambiar matricula a estado SUSPENDIDA'
            })
        
        # Check: Matrículas activas con ciclo no ACTIVO
        matriculas_ciclo_invalido = base_qs.filter(
            estado='ACTIVA'
        ).exclude(
            ciclo_academico__estado='ACTIVO'
        ).select_related('curso', 'estudiante', 'ciclo_academico')
        
        for m in matriculas_ciclo_invalido:
            issues.append({
                'id': m.id,
                'type': 'MATRICULA_CICLO_INVALIDO',
                'description': f'Matricula #{m.id} activa pero ciclo no está ACTIVO',
                'suggested_action': 'Cambiar matricula a estado SUSPENDIDA o actualizar ciclo_academico'
            })
        
        # Check: Matrículas con NULL curso
        matriculas_sin_curso = base_qs.filter(
            estado='ACTIVA',
            curso__isnull=True
        ).select_related('estudiante', 'ciclo_academico')
        
        for m in matriculas_sin_curso:
            issues.append({
                'id': m.id,
                'type': 'MATRICULA_SIN_CURSO',
                'description': f'Matricula #{m.id} activa sin curso asignado',
                'suggested_action': 'Asignar curso o cambiar estado a SUSPENDIDA'
            })
        
        # Check: Matrículas con NULL ciclo_academico
        matriculas_sin_ciclo = base_qs.filter(
            estado='ACTIVA',
            ciclo_academico__isnull=True
        ).select_related('curso', 'estudiante')
        
        for m in matriculas_sin_ciclo:
            issues.append({
                'id': m.id,
                'type': 'MATRICULA_SIN_CICLO',
                'description': f'Matricula #{m.id} activa sin ciclo académico',
                'suggested_action': 'Asignar ciclo académico o cambiar estado'
            })
        
        return {
            'count': len(issues),
            'issues': issues
        }
    
    @staticmethod
    def _audit_cursos(rbd_colegio=None):
        """Auditar registros de Curso por relaciones inválidas"""
        issues = []
        
        # Base queryset
        base_qs = Curso.objects.all()
        if rbd_colegio:
            base_qs = base_qs.filter(colegio__rbd=rbd_colegio)
        
        # Check: Cursos activos con ciclo no ACTIVO
        cursos_ciclo_invalido = base_qs.filter(
            activo=True
        ).exclude(
            ciclo_academico__estado='ACTIVO'
        ).select_related('ciclo_academico', 'colegio')
        
        for c in cursos_ciclo_invalido:
            issues.append({
                'id': c.id_curso,
                'type': 'CURSO_CICLO_INVALIDO',
                'description': f'Curso "{c.nombre}" activo pero ciclo no está ACTIVO',
                'suggested_action': 'Marcar curso como inactivo (activo=False)'
            })
        
        # Check: Cursos con NULL ciclo_academico
        cursos_sin_ciclo = base_qs.filter(
            activo=True,
            ciclo_academico__isnull=True
        ).select_related('colegio')
        
        for c in cursos_sin_ciclo:
            issues.append({
                'id': c.id_curso,
                'type': 'CURSO_SIN_CICLO',
                'description': f'Curso "{c.nombre}" activo sin ciclo académico',
                'suggested_action': 'Asignar ciclo académico o marcar como inactivo'
            })
        
        return {
            'count': len(issues),
            'issues': issues
        }
    
    @staticmethod
    def _audit_clases(rbd_colegio=None):
        """Auditar registros de Clase por relaciones inválidas"""
        issues = []
        
        # Base queryset
        base_qs = Clase.objects.all()
        if rbd_colegio:
            base_qs = base_qs.filter(colegio__rbd=rbd_colegio)
        
        # Check: Clases activas con curso inactivo
        clases_curso_inactivo = base_qs.filter(
            activo=True,
            curso__activo=False
        ).select_related('curso', 'asignatura', 'profesor', 'colegio')
        
        for c in clases_curso_inactivo:
            issues.append({
                'id': c.id,
                'type': 'CLASE_CURSO_INACTIVO',
                'description': f'Clase #{c.id} activa pero curso está inactivo',
                'suggested_action': 'Desactivar clase (activo=False)'
            })
        
        # Check: Clases activas con profesor inactivo
        clases_profesor_inactivo = base_qs.filter(
            activo=True,
            profesor__is_active=False
        ).select_related('curso', 'asignatura', 'profesor', 'colegio')
        
        for c in clases_profesor_inactivo:
            issues.append({
                'id': c.id,
                'type': 'CLASE_PROFESOR_INACTIVO',
                'description': f'Clase #{c.id} activa pero profesor está inactivo',
                'suggested_action': 'Desactivar clase o reasignar profesor'
            })
        
        # Check: Clases activas donde curso tiene ciclo inválido
        clases_ciclo_invalido = base_qs.filter(
            activo=True
        ).exclude(
            curso__ciclo_academico__estado='ACTIVO'
        ).select_related('curso', 'curso__ciclo_academico', 'asignatura', 'profesor')
        
        for c in clases_ciclo_invalido:
            issues.append({
                'id': c.id,
                'type': 'CLASE_CICLO_INVALIDO',
                'description': f'Clase #{c.id} activa pero ciclo del curso no está ACTIVO',
                'suggested_action': 'Desactivar clase (activo=False)'
            })
        
        return {
            'count': len(issues),
            'issues': issues
        }
    
    @staticmethod
    def _audit_users(rbd_colegio=None):
        """Auditar registros de User por referencias huérfanas al colegio"""
        issues = []
        
        # Base queryset
        base_qs = User.objects.filter(
            rbd_colegio__isnull=False,
            is_active=True
        )
        
        if rbd_colegio:
            base_qs = base_qs.filter(rbd_colegio=rbd_colegio)
        
        base_qs = base_qs.select_related('role')
        
        for u in base_qs:
            # Check if colegio exists
            try:
                colegio = Colegio.objects.get(rbd=u.rbd_colegio)
            except Colegio.DoesNotExist:
                issues.append({
                    'id': u.id,
                    'type': 'USER_COLEGIO_HUERFANO',
                    'description': f'Usuario tiene rbd_colegio={u.rbd_colegio} pero el colegio no existe',
                    'suggested_action': 'Reasignar a colegio válido o desactivar usuario'
                })
        
        return {
            'count': len(issues),
            'issues': issues
        }
    
    @staticmethod
    def _audit_perfil_estudiante(rbd_colegio=None):
        """Auditar registros de PerfilEstudiante por ciclo_actual inválido"""
        issues = []
        
        # Base queryset
        base_qs = PerfilEstudiante.objects.all()
        if rbd_colegio:
            base_qs = base_qs.filter(user__rbd_colegio=rbd_colegio)
        
        # Check: Perfiles activos con ciclo_actual no ACTIVO
        perfiles_ciclo_invalido = base_qs.filter(
            estado_academico='Activo',
            ciclo_actual__isnull=False
        ).exclude(
            ciclo_actual__estado='ACTIVO'
        ).select_related('user', 'ciclo_actual')
        
        for p in perfiles_ciclo_invalido:
            issues.append({
                'id': p.id,
                'type': 'PERFIL_CICLO_INVALIDO',
                'description': f'PerfilEstudiante #{p.id} activo pero ciclo_actual no está ACTIVO',
                'suggested_action': 'Actualizar ciclo_actual o cambiar estado_academico'
            })
        
        # Check: Perfiles activos con NULL ciclo_actual
        perfiles_sin_ciclo = base_qs.filter(
            estado_academico='Activo',
            ciclo_actual__isnull=True
        ).select_related('user')
        
        for p in perfiles_sin_ciclo:
            issues.append({
                'id': p.id,
                'type': 'PERFIL_SIN_CICLO',
                'description': f'PerfilEstudiante #{p.id} activo sin ciclo_actual asignado',
                'suggested_action': 'Asignar ciclo_actual o cambiar estado_academico'
            })
        
        # Check: Perfiles activos con usuario inactivo
        perfiles_user_inactivo = base_qs.filter(
            estado_academico='Activo',
            user__is_active=False
        ).select_related('user')
        
        for p in perfiles_user_inactivo:
            issues.append({
                'id': p.id,
                'type': 'PERFIL_USER_INACTIVO',
                'description': f'PerfilEstudiante #{p.id} activo pero User está inactivo',
                'suggested_action': 'Cambiar estado_academico a "Suspendido" o reactivar usuario'
            })
        
        return {
            'count': len(issues),
            'issues': issues
        }
    
    @staticmethod
    def _determine_severity(issue_type):
        """
        Determina la severidad de un problema basado en su tipo.
        
        Args:
            issue_type (str): Tipo de problema
            
        Returns:
            str: 'critical' o 'warning'
        """
        # Problemas críticos que impiden operación normal
        critical_types = [
            'MATRICULA_SIN_CICLO',
            'CURSO_SIN_CICLO',
            'USER_COLEGIO_HUERFANO',
            'PERFIL_SIN_CICLO'
        ]
        
        if issue_type in critical_types:
            return 'critical'
        else:
            return 'warning'
