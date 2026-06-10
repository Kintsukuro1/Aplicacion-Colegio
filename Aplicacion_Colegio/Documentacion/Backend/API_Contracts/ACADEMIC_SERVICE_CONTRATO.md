# Academic Service - Contrato del Dominio Académico

## Problema Original

La Fase 3 inicialmente se completó con la implementación del modelo temporal (CicloAcademico), pero persistía un problema de arquitectura:

- **Exceso de capas sin contrato explícito**
- Tendencia a crear servicios separados por "conveniencia" (ej: `academic_view_service.py`, `academic_reports_service.py`)
- Límites borrosos entre responsabilidades
- Fragmentación del dominio académico

## Solución: Servicio Académico Unificado

Se implementó `AcademicService` como **único punto de entrada para todo el dominio académico**, con contrato explícito y responsabilidades claramente definidas.

### Principios Aplicados

1. **Regla 5 del proyecto:** "Una app = un dominio"
2. **Separación por responsabilidades del negocio**, no por capas técnicas
3. **Contrato explícito:** Cada método tiene una responsabilidad única y clara
4. **Consolidación:** Todas las operaciones académicas en un solo servicio

## Responsabilidades Consolidadas

### 1. Gestión Curricular
```python
AcademicService.gestionar_curso(user, curso_id, data, action)
# Crear, actualizar, eliminar cursos con validaciones de integridad
```

### 2. Control de Asistencia
```python
AcademicService.registrar_asistencia(user, clase_id, asistencias_data)
AcademicService.obtener_asistencia_curso(user, curso_id, fecha_inicio, fecha_fin)
# Registro y consulta de asistencia por clase/curso
```

### 3. Gestión de Calificaciones
```python
AcademicService.registrar_calificaciones(user, evaluacion_id, calificaciones_data)
AcademicService.obtener_calificaciones_estudiante(user, estudiante_id, asignatura_id)
# Registro y consulta de notas por evaluación/estudiante
```

### 4. Reportes Académicos
```python
AcademicService.generar_reporte_academico(user, tipo_reporte, filtros)
# Reportes consolidados: curso, asignatura, estudiante, general
```

## Control de Acceso

Cada método está protegido con permisos granulares:

- `@PermissionService.require_permission('ACADEMICO.MANAGE_CURRICULUM')`
- `@PermissionService.require_permission('ACADEMICO.MANAGE_ATTENDANCE')`
- `@PermissionService.require_permission('ACADEMICO.MANAGE_GRADES')`
- `@PermissionService.require_permission('ACADEMICO.VIEW_REPORTS')`

## Beneficios Arquitectónicos

### ✅ Lo que se logró
- **Dominio consolidado:** Una sola fuente de verdad para lógica académica
- **Contratos explícitos:** Cada método tiene responsabilidad única
- **Mantenibilidad:** Cambios en reglas académicas en un solo lugar
- **Testabilidad:** Servicio completo testeable como unidad
- **Seguridad:** Permisos centralizados y consistentes

### ❌ Lo que se evitó
- **Fragmentación:** No más `academic_view_service.py` + `academic_reports_service.py`
- **Duplicación:** Lógica académica no se reparte en múltiples archivos
- **Inconsistencia:** Reglas académicas centralizadas
- **Complejidad:** Patrón simple y directo

## Patrón de Uso

```python
# En vistas o otros servicios:
from backend.apps.core.services.academic_service import AcademicService

# Registrar asistencia
resultado = AcademicService.registrar_asistencia(
    request.user,
    clase_id=123,
    asistencias_data=[{'estudiante_id': 1, 'estado': 'PRESENTE'}]
)

# Generar reporte
reporte = AcademicService.generar_reporte_academico(
    request.user,
    'curso',
    {'curso_id': 456}
)
```

## Evolución Futura

Si el dominio académico crece significativamente, se subdividirá por **reglas de negocio**, no por capas técnicas:

- `AcademicCurriculumService` (gestión curricular)
- `AcademicAssessmentService` (evaluaciones y calificaciones)
- `AcademicReportingService` (reportes y análisis)

Pero **solo cuando la complejidad del dominio lo exija**, no por anticipación.

## Conclusión

`AcademicService` representa la madurez arquitectónica alcanzada en Fase 3: **un dominio consolidado con contratos explícitos**, eliminando la tentación de crear capas innecesarias por "no saber dónde poner algo".</content>
<parameter name="filePath">c:\Proyectos\Aplicacion_Colegio\backend\apps\core\services\ACADEMIC_SERVICE_CONTRATO.md