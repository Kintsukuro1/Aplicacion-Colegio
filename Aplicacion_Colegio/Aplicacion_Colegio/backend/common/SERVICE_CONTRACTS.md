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
Usar type hints obligatoriamente:
```python
def metodo(self, user: User, data: dict) -> dict:
```

### 5. Validación de Contratos
Todo service debe tener tests que validen cumplimiento de contrato.

---

## TIPOS DE OPERACIONES

### 1. Query Operations (Consultas)
**Retornan:** `dict` estructurado

```python
{
    'success': bool,        # OBLIGATORIO: true si operación exitosa
    'data': Any,           # OBLIGATORIO: resultado de la consulta
    'error': Optional[Dict], # OPCIONAL: dict de ErrorResponseBuilder si falla
    'metadata': dict       # OPCIONAL: información adicional
}
```

**Ejemplos:**
```python
# ✅ Correcto
{
    'success': True,
    'data': {'user_id': 1, 'name': 'Juan'},
    'metadata': {'cached': False, 'timestamp': '2026-02-17'}
}

# ✅ Correcto con error
{
    'success': False,
    'data': None,
    'error': {
        'error_type': 'NOT_FOUND',
        'user_message': 'Usuario no encontrado',
        'action_url': '/dashboard/',
        'context': {'user_id': 999}
    }
}

# ❌ Incorrecto - falta 'success'
{
    'data': {'user_id': 1}
}

# ❌ Incorrecto - error como string
{
    'success': False,
    'error': 'Usuario no encontrado'  # Debe ser dict de ErrorResponseBuilder
}
```

### 2. Command Operations (Comandos)
**Retornan:** `dict` estructurado

```python
{
    'success': bool,          # OBLIGATORIO: true si comando exitoso
    'message': str,           # OBLIGATORIO: mensaje descriptivo
    'data': Any,     # Datos resultantes (opcional)
    'error': str,    # Solo si success=False
    'code': str      # Código de error (opcional)
}
```

**Ejemplos:**
```python
# Comando exitoso
{
    'success': True,
    'message': 'Usuario creado exitosamente',
    'data': {'user_id': 123}
}

# Comando fallido
{
    'success': False,
    'error': 'Email ya existe',
    'code': 'DUPLICATE_EMAIL'
}
```

### 3. Operaciones de Validación (Validation Operations)

**Retornan:** `tuple` consistente

```python
(bool, str)  # (es_valido, mensaje)
```

**Ejemplos:**
```python
(True, None)  # Válido
(False, "Campo requerido: email")  # Inválido con mensaje
```

### 4. Operaciones de Transformación (Transform Operations)

**Retornan:** El objeto transformado directamente

```python
Any  # El resultado de la transformación
```

**Ejemplos:**
```python
"sidebar_admin.html"  # Template path
{'total': 150, 'activos': 120}  # Estadísticas calculadas
```

## Reglas de Contratos

### Regla 1: Un Método = Un Contrato
Cada método debe seguir **estrictamente** un tipo de contrato.

### Regla 2: Consistencia en el Dominio
Todos los métodos de un mismo dominio usan contratos similares.

### Regla 3: Docstrings Formales Obligatorias
```python
@staticmethod
def metodo_ejemplo(param1, param2):
    """
    Descripción clara de qué hace el método.

    Args:
        param1 (Tipo): Descripción del parámetro
        param2 (Tipo): Descripción del parámetro

    Returns:
        dict: {
            'success': bool - Indica si la operación fue exitosa
            'data': Tipo - Los datos resultantes
            'error': str - Mensaje de error (solo si success=False)
        }

    Raises:
        ValidationError: Cuando los parámetros son inválidos
    """
```

### Regla 4: Tipos Explícitos
Usar type hints cuando sea posible:
```python
def metodo(self, user: User, data: dict) -> dict:
```

## Migración de Servicios Existentes

### DashboardAuthService
- `get_user_context()` → Query Operation (dict)
- `get_sidebar_template()` → Transform Operation (str)
- `validate_page_access()` → Validation Operation (tuple)

### AcademicService
- `gestionar_curso()` → Command Operation (dict)
- `registrar_asistencia()` → Command Operation (dict)
- `obtener_*()` → Query Operation (dict)

## Beneficios

✅ **Predecibilidad**: Siempre sabes qué retorna un método
✅ **Mantenibilidad**: Contratos claros facilitan cambios
✅ **Testabilidad**: Tests pueden validar contratos
✅ **Documentación**: Docstrings sirven como especificación
✅ **Consistencia**: Patrón uniforme en toda la aplicación

## Implementación

1. Actualizar docstrings de todos los services existentes
2. Migrar tipos de retorno inconsistentes
3. Crear tests que validen contratos
4. Documentar contratos en este archivo</content>
<parameter name="filePath">c:\Proyectos\Aplicacion_Colegio\backend\common\SERVICE_CONTRACTS.md