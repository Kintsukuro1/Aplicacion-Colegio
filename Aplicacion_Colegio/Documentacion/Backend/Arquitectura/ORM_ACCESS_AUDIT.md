# Auditoría de Acceso ORM (Fase 1)

Fecha: 2026-02-26
Scope: `backend/`
Patrones auditados: `.objects.create(`, `.objects.get(`, `.objects.filter(`, `.objects.update(`, `.objects.delete(`

## Resumen ejecutivo

Se detectan accesos directos al ORM fuera de la capa `services`, incluyendo escrituras (`create`) en `views`, `signals` y `management/commands`.
Esto viola el principio objetivo del roadmap:

`View → Service → IntegrityService → ORM`

## Avance Fase 2 (2026-02-26)

Se migraron operaciones críticas de nivel 1 para que las vistas ya no escriban directo en ORM para:

- `Colegio`
- `CicloAcademico`
- `Curso`
- `Clase` (bulk update por asignatura)

Servicios incorporados/extendidos:

- `backend/apps/core/services/colegio_service.py`
- `backend/apps/core/services/ciclo_academico_service.py`
- `backend/apps/core/services/curso_service.py`
- `backend/apps/core/services/clase_service.py`
- `backend/apps/core/services/admin_school_service.py` (extendido)

Views migradas:

- `backend/apps/core/views/admin_general/escuelas.py`
- `backend/apps/core/views/admin_escolar/gestionar_ciclos.py`
- `backend/apps/core/views/admin_escolar/gestionar_cursos.py`
- `backend/apps/core/views/admin_escolar/setup_wizard.py`
- `backend/apps/core/views/admin_escolar/gestionar_asignaturas.py`

Estado actual en `backend/apps/core/views/**` para entidades críticas de nivel 1:

- Sin coincidencias de `.objects.create/.update/.delete` para `Colegio`, `CicloAcademico`, `Curso`, `Matricula`, `Clase`.

## Avance Fase 2 N2 (2026-02-26)

Se cerró la capa contractual para entidades de nivel 2 en servicios:

- `UserService` (`create_user`, `change_role`) con validación de colegio, unicidad y consistencia rol/perfil.
- `AcademicProfileService` (`create_student_profile`, `create_teacher_profile`) con validación obligatoria de rol y colegio.
- `MatriculaService` establecido como contrato público de comando (`create`, `change_status`, `delete`) delegando en la implementación legacy `MatriculasService` + `IntegrityService`.
- `SubscriptionService` (`upsert_school_subscription`, `change_status`) para centralizar suscripción por colegio.

Migraciones aplicadas:

- `backend/apps/core/views/admin_escolar/setup_wizard.py`
  - creación de usuarios profesor/apoderado/estudiante ahora vía `UserService`.
  - creación de perfiles profesor/estudiante vía `AcademicProfileService`.
- `backend/apps/core/services/escuela_management_service.py`
  - cambio de plan de colegio ahora vía `SubscriptionService`.
  - creación de admin escolar ahora vía `UserService`.

Estado actual de escrituras directas en `backend/apps/core/views/**` para N1+N2:

- Sin coincidencias para mutaciones directas de `User`, `PerfilEstudiante`, `PerfilProfesor`, `Subscription`, `Matricula`.

## Cierre adicional (2026-02-26)

Se eliminó el remanente de write directo en vista de profesor para `MaterialClase`:

- `backend/apps/core/views/profesor/mis_clases.py`
  - `ver_detalle_clase` ahora delega en `ClassDetailService`.
- `backend/apps/core/services/class_detail_service.py`
  - operaciones de material delegadas a `MaterialClaseService`.
- `backend/apps/academico/services/material_clase_service.py` (nuevo)
  - `create`, `deactivate`, `toggle_visibility` con validación de integridad por colegio.

## Inicio Fase 3 (2026-02-26)

Se creó la base de tests de invariantes en:

- `tests/unit/domain_invariants/test_domain_invariants_phase3.py`

Cobertura inicial implementada (4/10-20 objetivo):

- No permitir crear curso sin ciclo activo (`CursoService.create`).
- No permitir matrícula cross-colegio (`MatriculaService.create`).
- No permitir clase sin profesor válido (`ClaseService.create`).
- No permitir operaciones con setup incompleto (`IntegrityService` vía `ClaseService.create`).

Estado inicial: **4 tests passing** en ejecución focalizada.

Actualización Fase 3 (2026-02-26, bloque ampliado):

- Suite ampliada a **12 tests** en `tests/unit/domain_invariants/test_domain_invariants_phase3.py`.
- Cobertura añadida:
  - bloqueo de doble matrícula activa por ciclo,
  - bloqueo de delete sobre matrícula activa,
  - delete permitido para matrícula no activa,
  - bloqueo de reactivación cuando ya existe activa,
  - bloqueo de clase con curso/asignatura inactivos,
  - bloqueo de eliminación de ciclo activo,
  - activación de ciclo con desactivación automática del ciclo activo previo.
- Todos los tests del bloque Fase 3 pasan: **12 passed**.

Bug de dominio detectado y corregido durante Fase 3:

- `MatriculasService._execute_create` consultaba `Curso.objects.get(id=...)` en lugar de `id_curso`.
- Corregido a `Curso.objects.get(id_curso=...)` para mantener coherencia con el modelo `Curso`.

## Verificación crítica ORM en capas no-service (2026-02-26)

Auditoría ejecutada para patrones:

- `.objects.create(`
- `.objects.get(`
- `.objects.filter(`
- `.objects.update(`
- `.objects.delete(`

Ámbitos revisados:

- `backend/apps/**/signals.py`
- `backend/apps/**/views.py`
- `backend/apps/**/serializers.py`
- adicionalmente `backend/apps/**/views/**/*.py` (estructura real del proyecto)

Resultado de migración aplicado:

- `backend/apps/comunicados/signals.py`
  - sin ORM directo; ahora delega en `ComunicadosService.notify_new_comunicado`.
- `backend/apps/core/views/admin_escolar/setup_wizard.py`
  - creación de `Apoderado` y relación apoderado-estudiante delegada a `ApoderadoService`.
- `backend/apps/core/views/estudiante/tareas.py`
  - entrega (`get_or_create`/`save`) delegada a `TareaEntregaService`.
- `backend/apps/core/views/admin_escolar/gestionar_infraestructura.py`
  - `create/update/delete` delegados a `InfraestructuraService`.
- `backend/apps/core/views/admin_escolar/gestionar_asignaturas.py`
  - `Asignatura.objects.create`, `BloqueHorario.objects.get_or_create` y `BloqueHorario.objects.create` delegados a `AsignaturaHorarioService`.
- `backend/apps/core/views/asesor_financiero/becas_api.py`
  - `Beca.objects.create` y auditoría de creación delegadas a `FinancialDocumentsService`.
- `backend/apps/core/views/asesor_financiero/boletas_api.py`
  - `Boleta.objects.create` y auditoría de creación delegadas a `FinancialDocumentsService`.

Estado actual de writes directos en `backend/apps/**/views/**/*.py` para patrones críticos:

- Sin coincidencias para `create/get_or_create/update_or_create/filter(...).update/delete`.

## Barrido estricto + revisión funcional (2026-02-26)

Barrido estricto ejecutado con los patrones:

- `.objects.create(`
- `.objects.filter(`
- `.objects.get(`
- `.objects.update(`
- `.objects.delete(`

Ámbitos:

- `backend/apps/**/views.py`
- `backend/apps/**/serializers.py`
- `backend/apps/**/signals.py`
- `backend/apps/**/views/**/*.py` (estructura real)

Resultado:

- `views.py`, `serializers.py`, `signals.py`: sin coincidencias directas de ORM write crítico.
- `views/**/*.py`: persisten accesos ORM de **lectura** (`get/filter`) en múltiples vistas.
- `views/**/*.py`: **sin writes directos críticos** (`create/get_or_create/update_or_create/filter(...).update/delete`).

Revisión de funcionamiento post-migración:

- `pytest tests/asesor_financiero/test_asesor_becas.py tests/asesor_financiero/test_asesor_pagos.py tests/asesor_financiero/test_asesor_dashboard_kpis.py tests/functional/test_setup_wizard_validation.py -q` → **23 passed**.
- `pytest tests/unit/domain_invariants/test_domain_invariants_phase3.py -q` → **12 passed**.
- `manage.py check` → **System check identified no issues (0 silenced)**.

## Pasada estricta final (2026-02-26, cierre)

Se ejecutó una pasada estricta adicional para remover accesos ORM directos en capas no-service (`views.py`, `views/**/*.py`, `serializers.py`, `signals.py`) y cerrar remanentes de lectura/escritura en views.

Migraciones aplicadas en esta pasada:

- Nuevos servicios de consulta/delegación:
  - `backend/apps/core/services/school_query_service.py`
  - `backend/apps/core/services/setup_wizard_query_service.py`
  - `backend/apps/core/services/academic_report_query_service.py`
  - `backend/apps/core/services/admin_general_escuelas_query_service.py`
  - `backend/apps/core/services/asignaturas_view_service.py`
- Views refactorizadas para delegar en servicios (sin ORM directo):
  - `backend/apps/core/views/admin_escolar/generar_informe_academico.py`
  - `backend/apps/core/views/admin_escolar/gestionar_asistencia_profesor.py`
  - `backend/apps/core/views/admin_escolar/gestionar_cursos.py`
  - `backend/apps/core/views/admin_escolar/gestionar_evaluaciones_calificaciones.py`
  - `backend/apps/core/views/admin_escolar/gestionar_asignaturas.py`
  - `backend/apps/core/views/admin_escolar/setup_wizard.py`
  - `backend/apps/core/views/admin_general/escuelas.py`
  - `backend/apps/mensajeria/views/clase.py`
- Extensión de servicio existente:
  - `backend/apps/mensajeria/services/mensajeria_service.py` (`get_class_for_messages`)

Resultado del barrido estricto final:

- `backend/apps/**/views.py`: sin coincidencias de `.objects.`
- `backend/apps/**/views/**/*.py`: sin coincidencias de `.objects.`
- `backend/apps/**/serializers.py`: sin coincidencias de `.objects.`
- `backend/apps/**/signals.py`: sin coincidencias de `.objects.`

Revisión funcional de cierre:

- `python manage.py check` → **sin issues**.
- `python -m pytest tests/unit/domain_invariants/test_domain_invariants_phase3.py -q` → **12 passed**.

## Revisión estructural dashboard services (2026-02-26)

Motivación: validar que `dashboard_service`, `dashboard_context_service`, `dashboard_orchestrator_service` no concentren lógica de dominio mutante y se mantengan como capa de orquestación/lectura.

Resultado de auditoría:

- En `backend/apps/core/services/dashboard*_service.py` se detectó un único punto de mutación de dominio:
  - `dashboard_orchestrator_service.py` persistía disponibilidad de profesor con `DisponibilidadProfesor.objects.get_or_create(...)/save()`.
- No se detectaron otras escrituras ORM directas (`create/get_or_create/update_or_create/save`) en dashboard services después del refactor.

Refactor aplicado:

- Nuevo service de dominio:
  - `backend/apps/accounts/services/teacher_availability_service.py`
  - contrato: `TeacherAvailabilityService.save_weekly_availability(...)`
  - responsabilidades: validación de rol, validación de integridad, resolución de bloques horarios y persistencia de disponibilidad.
- `dashboard_orchestrator_service.py` ahora delega al service anterior y elimina mutación ORM directa.

Verificación posterior:

- barrido en `backend/apps/core/services/dashboard*_service.py` para patrones de escritura ORM: **sin coincidencias**.
- `python manage.py check`: **OK**.

## Conteo por tipo de archivo (todos los patrones)

- `services`: 385
- `views`: 134
- `scripts/commands`: 33
- `signals`: 7
- `other`: 38

## Hallazgos críticos: escrituras directas fuera de services

### 1) Views (migración obligatoria)

- `backend/apps/core/views/admin_escolar/gestionar_cursos.py`
  - `Curso.objects.create(...)`
  - Acción: mover a `CursoService.create(...)`

- `backend/apps/core/views/admin_escolar/gestionar_ciclos.py`
  - `CicloAcademico.objects.create(...)`
  - Acción: mover a `CicloAcademicoService.create(...)`

- `backend/apps/core/views/admin_escolar/setup_wizard.py`
  - `CicloAcademico.objects.create(...)`
  - `Curso.objects.create(...)`
  - `Apoderado.objects.create(...)`
  - `RelacionApoderadoEstudiante.objects.create(...)`
  - Acción: mover a `CicloAcademicoService`, `CursoService`, `ApoderadoService`, `Matricula/RelacionService`

- `backend/apps/core/views/admin_escolar/gestionar_asignaturas.py`
  - `Asignatura.objects.create(...)`
  - `BloqueHorario.objects.create(...)`
  - Acción: mover a `AsignaturaService` / `HorarioService`

- `backend/apps/core/views/admin_escolar/gestionar_infraestructura.py`
  - `Infraestructura.objects.create(...)`
  - Acción: mover a `InfraestructuraService.create(...)`

- `backend/apps/core/views/admin_general/escuelas.py`
  - `Colegio.objects.create(...)`
  - Acción: mover a `EscuelaManagementService.create_school(...)`

- `backend/apps/core/views/profesor/mis_clases.py`
  - `MaterialClase.objects.create(...)`
  - Acción: mover a `ClassDetailService` o `MaterialClaseService`

- `backend/apps/core/views/asesor_financiero/becas_api.py`
  - `Beca.objects.create(...)`
  - `AuditoriaEvento.objects.create(...)`
  - Acción: mover a `BecaService` / `AuditoriaService`

- `backend/apps/core/views/asesor_financiero/boletas_api.py`
  - `Boleta.objects.create(...)`
  - `AuditoriaEvento.objects.create(...)`
  - Acción: mover a `BoletaService` / `AuditoriaService`

### 2) Signals (validar y encapsular)

- `backend/apps/comunicados/signals.py`
  - `Notificacion.objects.create(...)`
  - Acción: encapsular en service idempotente o evento de dominio para evitar efectos colaterales silenciosos.

### 3) Scripts / management commands (migración obligatoria)

- `backend/apps/core/management/commands/fix_student_data.py`
  - `PerfilEstudiante.objects.create(...)`
  - `CicloAcademico.objects.create(...)`
  - `NivelEducativo.objects.create(...)`
  - `Curso.objects.create(...)`
  - `Matricula.objects.create(...)`
  - Acción: reemplazar por services transaccionales con validación de integridad.

### 4) Other (fuera de views/services)

- `backend/apps/accounts/models.py`
  - `FirmaDigitalApoderado.objects.create(...)`
  - Acción: revisar si corresponde mantener en modelo o mover a service de firma/documentos.

- `backend/apps/core/models_mejorados.py`
  - `CambioEstado.objects.create(...)`
  - `CambioEstadoMatricula.objects.create(...)`
  - Acción: evaluar si son side-effects permitidos del dominio o deben pasar por service/evento.

## Entidades críticas del roadmap: cobertura actual observada

Con escritura directa fuera de services detectada en:

- `Colegio`
- `CicloAcademico`
- `Curso`
- `Matricula`
- `Usuario` (vía importaciones masivas en services ya existentes)

Pendiente validar en Fase 2/3 para cobertura completa:

- `Clase` (no se detectan writes directos críticos en views; mantener control en servicios)

## Observaciones técnicas

- No se detectaron coincidencias de `.objects.update(` ni `.objects.delete(` con el patrón exacto auditado.
- Sí existen operaciones mutables tipo `QuerySet.update()` / `QuerySet.delete()` (ej. `Model.objects.filter(...).update(...)`) en varias views/services; deben considerarse en una segunda pasada de endurecimiento.

## Backlog inmediato (Fase 2 sugerida)

1. Migrar primero `admin_escolar/setup_wizard.py` (alto impacto + múltiples entidades críticas).
2. Migrar `gestionar_cursos.py` y `gestionar_ciclos.py` a services con `IntegrityService` obligatorio.
3. Migrar `fix_student_data.py` para eliminar escrituras directas en command.
4. Encapsular `comunicados/signals.py` en servicio/evento idempotente.
5. Definir regla de lint/revisión: bloquear `.objects.create(` fuera de `*/services/*` y tests.

## Regla operativa desde esta fase

No aceptar nuevos PRs con:

- `.objects.create(` fuera de `services` (o tests)
- escrituras directas en `views`, `signals`, `commands`

Cualquier excepción debe documentarse explícitamente con justificación de dominio.
