# CONTRATOS DEL SISTEMA - FASE 6
## ⚠️ DOCUMENTO CONGELADO - NO MODIFICAR SIN REVISIÓN ⚠️

**Última actualización**: 2026-02-17  
**Estado**: CONGELADO - Contratos inmutables  
**Propósito**: Establecer contratos formales antes de construcción de UI comercial

---

## ÍNDICE
1. [Principios de Contratos](#principios-de-contratos)
2. [Tipos de Operaciones](#tipos-de-operaciones)
3. [Contrato de ErrorResponseBuilder](#contrato-de-errorresponsebuilder)
4. [Contratos de Services Críticos](#contratos-de-services-críticos)
5. [Estados Válidos del Sistema](#estados-válidos-del-sistema)
6. [Reglas de Inmutabilidad](#reglas-de-inmutabilidad)
7. [Tests de Validación](#tests-de-validación)

---

## PRINCIPIOS DE CONTRATOS

### 1. Un Método = Un Contrato
Cada método debe seguir **estrictamente** un tipo de contrato. No mezclar patrones.

### 2. Contratos Son Inmutables
Una vez definido un contrato en Fase 6, **NO puede cambiar** sin proceso formal de migración.

### 3. Docstrings Formales Obligatorias
Todo método público debe documentar explícitamente su contrato.

### 4. Tipos Explícitos
Usar type hints obligatoriamente cuando sea posible:
```python
def metodo(self, user: User, data: dict) -> dict:
```

### 5. Validación de Contratos
Todo service debe tener tests que validen cumplimiento de contrato.

---

## TIPOS DE OPERACIONES

###  1. Query Operations (Consultas)
**Propósito**: Obtener datos del sistema  
**Retornan**: `dict` estructurado

```python
{
    'success': bool,          # OBLIGATORIO: true si operación exitosa
    'data': Any,              # OBLIGATORIO: resultado de la consulta (None si falla)
    'error': Optional[Dict],  # OPCIONAL: dict de ErrorResponseBuilder si falla
    'metadata': Optional[dict] # OPCIONAL: información adicional
}
```

**Ejemplos válidos:**
```python
# ✅ Query exitosa
{
    'success': True,
    'data': {'user_id': 1, 'name': 'Juan'},
    'metadata': {'cached': False}
}

# ✅ Query fallida con error estructurado
{
    'success': False,
    'data': None,
    'error': {
        'error_type': 'NOT_FOUND',
        'user_message': 'Usuario no encontrado',
        'action_url': '/dashboard/',
        'context': {

 'user_id': 999}
    }
}
```

**Ejemplos incorrectos:**
```python
# ❌ Falta 'success'
{'data': {'user_id': 1}}

# ❌ Error como string en lugar de dict
{'success': False, 'error': 'No encontrado'}

# ❌ Retorna None en lugar de dict
return None  # Prohibido para Query Operations
```

### 2. Command Operations (Comandos)
**Propósito**: Modificar estado del sistema  
**Retornan**: `dict` estructurado

```python
{
    'success': bool,           # OBLIGATORIO: true si comando exitoso
    'message': str,            # OBLIGATORIO: mensaje descriptivo
    'data': Optional[Any],     # OPCIONAL: datos resultantes
    'error': Optional[Dict],   # OPCIONAL: dict de ErrorResponseBuilder si falla
}
```

**Ejemplos válidos:**
```python
# ✅ Comando exitoso
{
    'success': True,
    'message': 'Usuario creado exitosamente',
    'data': {'user_id': 123}
}

# ✅ Comando fallido
{
    'success': False,
    'message': 'No se pudo crear usuario',
    'error': {
        'error_type': 'VALIDATION_ERROR',
        'user_message': 'Email ya existe',
        'action_url': '/users/create/',
        'context': {'field': 'email'}
    }
}
```

### 3. Validation Operations (Validaciones)
**Propósito**: Validar prerequisites o condiciones  
**Retornan**: `Optional[Dict]` - None si válido, Dict de error si inválido

```python
# Retorna None si válido
None

# Retorna dict de ErrorResponseBuilder si inválido
{
    'error_type': str,
    'user_message': str,
    'action_url': str,
    'context': dict
}
```

**Ejemplos válidos:**
```python
# ✅ Validación pasó
return None

# ✅ Validación falló
return ErrorResponseBuilder.build('MISSING_CICLO_ACTIVO', context={
    'colegio_id': colegio.id
})
```

**Ejemplos incorrectos:**
```python
# ❌ Retorna tuple
return (False, "Error de validación")

# ❌ Retorna string
return "Validación falló"

# ❌ Retorna bool
return False
```

### 4. Auth Operations (Autenticación)
**Propósito**: Autenticar y autorizar usuarios  
**Retornan**: `dict` estructurado especial

```python
{
    'success': bool,       # OBLIGATORIO: true si auth exitosa
    'user': Optional[User], # OBLIGATORIO: User object si success=True, None si False
    'error': Optional[Dict] # OPCIONAL: dict de ErrorResponseBuilder si falla
}
```

---

## CONTRATO DE ErrorResponseBuilder

### Estructura Inmutable
```python
{
    'error_type': str,      # OBLIGATORIO: Constante de error (ej: 'MISSING_CICLO_ACTIVO')
    'user_message': str,    # OBLIGATORIO: Mensaje user-friendly
    'action_url': str,      # OBLIGATORIO: URL donde usuario debe ir
    'context': dict         # OBLIGATORIO: Contexto adicional (puede ser {})
}
```

### Tipos de Error Congelados

#### Errores de Setup (Onboarding)
- `MISSING_CICLO_ACTIVO` - No existe ciclo académico activo
- `MISSING_COURSES` - No existen cursos creados
- `MISSING_TEACHERS_ASSIGNED` - No hay profesores asignados
- `MISSING_STUDENTS_ENROLLED` - No hay estudiantes matriculados
- `SCHOOL_NOT_CONFIGURED` - Configuración inicial incompleta

#### Errores de Validación
- `INVALID_PREREQUISITE` - Faltan prerequisitos
- `INVALID_CURSO_STATE` - Curso en estado inválido
- `INVALID_MATRICULA_STATE` - Matrícula en estado inválido
- `VALIDATION_ERROR` - Error de validación de campos
- `AUTHENTICATION_FAILED` - Autenticación fallida

#### Errores de Permisos
- `PERMISSION_DENIED` - Sin permisos para acción
- `NOT_FOUND` - Recurso no encontrado

#### Errores de Integridad
- `DATA_INCONSISTENCY` - Datos corruptos/contradictorios
- `INVALID_RELATIONSHIP` - FK a entidad inexistente/inactiva
- `ORPHANED_ENTITY` - Entidad sin padre válido
- `STATE_MISMATCH` - Estados incompatibles entre relacionados
- `INVALID_STATE` - Estado individual inválido

### Uso Obligatorio
```python
# ✅ Correcto
error = ErrorResponseBuilder.build('PERMISSION_DENIED', context={
    'user_role': user.role.nombre,
    'required_roles': ['Administrador'],
    'login_type': 'staff'
})
return {'success': False, 'error': error}

# ❌ Incorrecto - string directo
return {'success': False, 'error': 'Sin permisos'}

# ❌ Incorrecto - dict manual
return {'success': False, 'error': {'message': 'Sin permisos'}}
```

---

## CONTRATOS DE SERVICES CRÍTICOS

### AuthService
**Archivo**: `backend/apps/accounts/services/auth_service.py`

#### AuthService.perform_login()
**Tipo**: Auth Operation  
**Signatura**:
```python
@staticmethod
def perform_login(
    request: HttpRequest, 
    username: str, 
    password: str, 
    captcha_response: str, 
    remember_me: bool = False, 
    login_type: str = 'student'
) -> dict:
```

**Contrato**:
```python
{
    'success': bool,       # True si login exitoso
    'user': Optional[User], # User object si success=True, None si False
    'error': Optional[Dict] # Dict de ErrorResponseBuilder si success=False
}
```

**Garantías**:
- Siempre retorna dict con 'success' y 'user'
- Si success=False, 'error' contiene ErrorResponseBuilder dict
- Nunca lanza excepciones no controladas
- Valida captcha si está habilitado
- Valida rol compatible con login_type

#### AuthService.validate_role_for_login_type()
**Tipo**: Validation Operation  
**Signatura**:
```python
@staticmethod
def validate_role_for_login_type(user: User, login_type: str) -> Optional[Dict]:
```

**Contrato**:
```python
# Retorna None si válido
# Retorna ErrorResponseBuilder dict si inválido
Optional[Dict]
```

**Garantías**:
- Retorna None si rol es compatible
- Retorna PERMISSION_DENIED si rol incompatible
- STAFF_ROLES = ['Profesor', 'Administrador general', 'Administrador escolar']
- STUDENT_ROLES = ['Alumno', 'Estudiante', 'Apoderado']

### DataRepairService
**Archivo**: `backend/apps/core/services/data_repair_service.py`

#### DataRepairService.repair_all()
**Tipo**: Command Operation  
**Signatura**:
```python
@staticmethod
def repair_all(rbd_colegio: int, dry_run: bool = False) -> dict:
```

**Contrato**:
```python
{
    'success': bool,
    'message': str,
    'categories': {
        'matriculas': {'count': int, 'details': list},
        'cursos': {'count': int, 'details': list},
        'clases': {'count': int, 'details': list},
        'usuarios': {'count': int, 'details': list},
        'perfiles': {'count': int, 'details': list}
    },
    'total_issues': int,
    'dry_run': bool
}
```

**Garantías**:
- Nunca elimina datos
- Solo marca como inactivo/suspendido
- Usa transacciones con rollback si dry_run=True
- No desactiva usuarios con matrículas activas

### SystemHealthService
**Archivo**: `backend/apps/core/services/system_health_service.py`

#### SystemHealthService.get_system_health()
**Tipo**: Query Operation  
**Signatura**:
```python
@staticmethod
def get_system_health(rbd_colegio: int) -> dict:
```

**Contrato**:
```python
{
    'success': bool,
    'data': {
        'status': str,  # 'healthy', 'warning', 'critical'
        'issues': list,
        'total_issues': int,
        'critical_issues': int,
        'warnings': int
    },
    'metadata': {
        'timestamp': str,
        'rbd_colegio': int
    }
}
```

**Garantías**:
- Siempre retorna estructura completa
- status basado en severidad de issues
- issues clasificados por tipo y severidad

### SetupService
**Archivo**: `backend/apps/core/services/setup_service.py`

#### SetupService.get_setup_status()
**Tipo**: Query Operation  
**Signatura**:
```python
@staticmethod
def get_setup_status(rbd_colegio: int) -> dict:
```

**Contrato**:
```python
{
    'success': bool,
    'data': {
        'setup_complete': bool,
        'missing_steps': list,
        'next_required_step': Optional[str],
        'is_legacy_school': bool
    }
}
```

**Garantías**:
- Detecta configuración legacy correctamente
- Lista pasos faltantes en orden lógico
- next_required_step es el más prioritario

---

## ESTADOS VÁLIDOS DEL SISTEMA

### Estados de Ciclo Académico
**Archivo**: `backend/apps/institucion/models.py`

```python
ESTADOS_CICLO = [
    ('ACTIVO', 'Activo'),       # Ciclo en curso
    ('CERRADO', 'Cerrado'),     # Ciclo finalizado
    ('PLANIFICACION', 'Planificación') # Ciclo futuro
]
```

**Transiciones Válidas**:
- PLANIFICACION → ACTIVO (inicio de año escolar)
- ACTIVO → CERRADO (fin de año escolar)
- ❌ CERRADO → ACTIVO (prohibido)

**Reglas de Negocio**:
- Solo puede haber 1 ciclo ACTIVO por colegio
- No se pueden crear matrículas en ciclos CERRADOS
- No se pueden crear cursos en ciclos CERRADOS

### Estados de Matrícula
**Archivo**: `backend/apps/matriculas/models.py`

```python
ESTADOS_MATRICULA = [
    ('ACTIVA', 'Activa'),
    ('SUSPENDIDA', 'Suspendida'),
    ('RETIRADA', 'Retirada'),
    ('GRADUADA', 'Graduada')
]
```

**Transiciones Válidas**:
- ACTIVA → SUSPENDIDA (suspensión temporal)
- ACTIVA → RETIRADA (retiro definitivo)
- ACTIVA → GRADUADA (graduación)
- SUSPENDIDA → ACTIVA (reactivación)
- ❌ RETIRADA → ACTIVA (prohibido)
- ❌ GRADUADA → cualquier otro (prohibido)

**Reglas de Negocio**:
- Matrícula ACTIVA requiere curso activo
- Matrícula ACTIVA requiere ciclo ACTIVO
- Matrícula SUSPENDIDA no permite asistencias/calificaciones

### Estados de Usuario
**Archivo**: `backend/apps/accounts/models.py`

```python
# Campo: is_active (bool)
ACTIVO = True
INACTIVO = False
```

**Reglas de Negocio**:
- Usuario INACTIVO no puede autenticarse
- Usuario INACTIVO no puede tener matrículas ACTIVAS
- Usuario INACTIVO con perfil de profesor no puede tener clases asignadas

### Estados de Curso
**Archivo**: `backend/apps/cursos/models.py`

```python
# Campo: activo (bool)
ACTIVO = True
INACTIVO = False
```

**Reglas de Negocio**:
- Curso INACTIVO no puede tener matrículas ACTIVAS
- Curso INACTIVO no puede tener clases activas
- Curso ACTIVO requiere ciclo ACTIVO

---

## REGLAS DE INMUTABILIDAD

### Nivel 1: Contratos de ErrorResponseBuilder
**Estado**: CONGELADO PERMANENTEMENTE

- Estructura de error dict no puede cambiar
- Tipos de error existentes no pueden modificarse
- Se pueden AGREGAR nuevos tipos pero NUNCA cambiar existentes

### Nivel 2:Structura de Responses de Services
**Estado**: CONGELADO HASTA FASE 9

- Query Operations siempre retornan `{'success', 'data', 'error', 'metadata'}`
- Command Operations siempre retornan `{'success', 'message', 'data', 'error'}`
- Validation Operations siempre retornan `Optional[Dict]`
- Auth Operations siempre retornan `{'success', 'user', 'error'}`

### Nivel 3: Estados Válidos
**Estado**: CONGELADO HASTA FASE 9

- Valores de estados no pueden cambiar
- Transiciones válidas no pueden cambiar
- Se pueden agregar nuevos estados pero con proceso de migración

### Nivel 4: Contratos de Services Críticos
**Estado**: CONGELADO HASTA FASE 9

- AuthService contracts no pueden cambiar
- DataRepairService contracts no pueden cambiar
- SystemHealthService contracts no pueden cambiar
- SetupService contracts no pueden cambiar

### Proceso de Cambio de Contrato (Si absolutamente necesario)
1. Documentar razón del cambio en BREAKING_CHANGES.md
2. Crear versión v2 del método (mantener v1)
3. Deprecar v1 con warning
4. Migrar consumers a v2
5. Eliminar v1 solo después de 2 releases

---

## TESTS DE VALIDACIÓN

### Test de Contrato de Query Operation
```python
def test_service_query_contract():
    """Valida que service respete contrato de Query Operation"""
    result = SomeService.some_query_method()
    
    # Validar estructura
    assert isinstance(result, dict)
    assert 'success' in result
    assert 'data' in result
    assert isinstance(result['success'], bool)
    
    # Si failed, debe tener error
    if not result['success']:
        assert 'error' in result
        assert isinstance(result['error'], dict)
        assert 'error_type' in result['error']
        assert 'user_message' in result['error']
```

### Test de Contrato de Command Operation
```python
def test_service_command_contract():
    """Valida que service respete contrato de Command Operation"""
    result = SomeService.some_command_method()
    
    assert isinstance(result, dict)
    assert 'success' in result
    assert 'message' in result
    assert isinstance(result['success'], bool)
    assert isinstance(result['message'], str)
    
    if not result['success']:
        assert 'error' in result
```

### Test de Contrato de Validation Operation
```python
def test_service_validation_contract():
    """Valida que service respete contrato de Validation Operation"""
    result = SomeService.some_validation_method()
    
    # Debe retornar None o Dict
    assert result is None or isinstance(result, dict)
    
    # Si es dict, debe ser ErrorResponseBuilder
    if result is not None:
        assert 'error_type' in result
        assert 'user_message' in result
        assert 'action_url' in result
        assert 'context' in result
```

---

## BENEFICIOS DE CONTRATOS CONGELADOS

### ✅ Predecibilidad
Siempre sabes qué esperar de un service. No hay sorpresas.

### ✅ Mantenibilidad
Cambios futuros no rompen contratos existentes.

### ✅ Testabilidad
Tests pueden validar contratos sin conocer implementación.

### ✅ Desarrolladores Nuevos
Onboarding rápido - contratos son documentación ejecutable.

### ✅ UI Confiable
Frontend puede asumir contratos y construir UI robusta.

### ✅ Comercialización
Producto estable permite ventas con confianza.

---

## CONCLUSIÓN

Este documento establece los contratos inmutables del sistema.

**Cualquier violación de estos contratos es un BUG CRÍTICO.**

**Cualquier cambio a estos contratos requiere proceso formal de migración.**

La Fase 6 termina cuando:
- ✅ Todos los services críticos están documentados
- ✅ Tests de contrato existen para cada service
- ✅ Estados válidos están documentados
- ✅ ErrorResponseBuilder está congelado
- ✅ Este documento está aprobado y congelado

**Fecha de congelación**: 2026-02-17  
**Aprobado por**: Sistema automatizado de validación  
**Próxima revisión**: Solo si bugs críticos lo requieren
