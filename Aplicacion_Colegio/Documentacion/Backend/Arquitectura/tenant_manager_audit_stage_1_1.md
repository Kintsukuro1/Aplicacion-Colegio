# Stage 1.1 - TenantManager Audit

Date: 2026-02-23
Scope: `backend/apps/*/models.py` (10 files)

## Inventory Table

| Model | Uses TenantManager | Filter Field | Required Action |
|---|---|---|---|
| academico.Planificacion | Yes | colegio_id | None |
| academico.PlanificacionObjetivo | Yes | planificacion__colegio_id | None |
| academico.PlanificacionActividad | Yes | planificacion__colegio_id | None |
| academico.PlanificacionRecurso | Yes | planificacion__colegio_id | None |
| academico.PlanificacionEvaluacion | Yes | planificacion__colegio_id | None |
| academico.Asistencia | Yes | colegio_id | None |
| academico.Evaluacion | Yes | colegio_id | None |
| academico.Calificacion | Yes | colegio_id | None |
| academico.MaterialClase | Yes | colegio_id | None |
| academico.Tarea | Yes | colegio_id | None |
| academico.EntregaTarea | Yes | tarea__colegio_id | None |
| academico.InformeAcademico | Yes | colegio_id | None |
| academico.DetalleInformeAcademico | Yes | informe__colegio_id | None |
| accounts.Role | No | - | Keep global |
| accounts.User | Yes | rbd_colegio | None |
| accounts.PerfilEstudiante | Yes | user__rbd_colegio | None |
| accounts.DisponibilidadProfesor | Yes | profesor__rbd_colegio | None |
| accounts.PerfilProfesor | Yes | user__rbd_colegio | None |
| accounts.Apoderado | Yes | user__rbd_colegio | None |
| accounts.RelacionApoderadoEstudiante | Yes | apoderado__user__rbd_colegio | None |
| accounts.FirmaDigitalApoderado | Yes | apoderado__user__rbd_colegio | None |
| accounts.PerfilAsesorFinanciero | Yes | user__rbd_colegio | None |
| auditoria.AuditoriaEvento | Yes | colegio_rbd | None |
| auditoria.ConfiguracionAuditoria | Yes | colegio_rbd | None |
| comunicados.Comunicado | Yes | colegio_id | None |
| comunicados.ConfirmacionLectura | Yes | comunicado__colegio_id | None |
| comunicados.AdjuntoComunicado | Yes | comunicado__colegio_id | None |
| comunicados.PlantillaComunicado | Yes | colegio_id | None |
| comunicados.EstadisticaComunicado | Yes | comunicado__colegio_id | None |
| cursos.Curso | Yes | colegio_id | None |
| cursos.Asignatura | Yes | colegio_id | None |
| cursos.Clase | Yes | colegio_id | None |
| cursos.BloqueHorario | Yes | colegio_id | None |
| cursos.ClaseEstudiante | Yes | clase__colegio_id | None |
| institucion.Region | No | - | Keep global |
| institucion.Comuna | No | - | Keep global |
| institucion.TipoEstablecimiento | No | - | Keep global |
| institucion.DependenciaAdministrativa | No | - | Keep global |
| institucion.NivelEducativo | No | - | Keep global |
| institucion.TipoInfraestructura | No | - | Keep global |
| institucion.Colegio | Yes | rbd | None |
| institucion.ColegioInfraestructura | Yes | colegio_id | None |
| institucion.Infraestructura | Yes | rbd_colegio | None |
| institucion.CicloAcademico | Yes | colegio_id | None |
| matriculas.Matricula | Yes | colegio_id | None |
| matriculas.Cuota | Yes | matricula__colegio_id | None |
| matriculas.Pago | Yes | cuota__matricula__colegio_id | None |
| matriculas.EstadoCuenta | Yes | colegio_id | None |
| matriculas.Beca | Yes | matricula__colegio_id | None |
| matriculas.Boleta | Yes | pago__cuota__matricula__colegio_id | None |
| mensajeria.Anuncio | Yes | clase__colegio_id | None |
| mensajeria.Conversacion | Yes | clase__colegio_id | None |
| mensajeria.Mensaje | Yes | conversacion__clase__colegio_id | None |
| notificaciones.Notificacion | Yes | destinatario__rbd_colegio | None |
| notificaciones.PreferenciaNotificacion | Yes | usuario__rbd_colegio | None |
| notificaciones.DispositivoMovil | Yes | usuario__rbd_colegio | None |
| subscriptions.Plan | No | - | Keep global |
| subscriptions.Subscription | Yes | colegio_id | None |
| subscriptions.UsageLog | Yes | subscription__colegio_id | None |

## Findings

- Total models audited: 59
- Tenant-protected models requiring protection: 0 pending
- Global models intentionally without TenantManager: 9

## Code changes applied

- Updated `accounts.User` manager to declare explicit TenantManager usage:
  - `UserManager` now inherits from `TenantManager`
  - `User.objects = UserManager(school_field='rbd_colegio')`
