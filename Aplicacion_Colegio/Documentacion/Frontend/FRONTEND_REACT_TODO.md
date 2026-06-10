# Frontend React To-Do

## Lo Que Vamos A Hacer
- [ ] Mejorar estandar de feedback en lotes (exitos, fallos, IDs y recomendaciones de reintento).
- [ ] Validar smoke tests de flujos Admin criticos despues de cada bloque.
- [ ] Definir y ejecutar regresion rapida de permisos por accion en vistas Admin.
- [ ] Extender acciones masivas a modulos Admin restantes segun prioridades operativas.

## Lo Que Estamos Haciendo
- [x] Crear paginas React MVP para roles con API disponible (asesor, inspector, psicologo, soporte, bibliotecario, coordinador, apoderado).
- [x] Completar acciones secundarias por rol en esas vistas MVP (inspector, psicologo, soporte y biblioteca).
- [x] Mejorar UX de acciones por ID (tablas/listas accionables y autofill de IDs en lugar de input manual).
	- [x] Selector de clase en atraso (Inspector Convivencia).
	- [x] Selector de recurso en publicar/despublicar (Bibliotecario).
	- [x] Autofill de IDs en Soporte (ticket_id y approval_request_id).
	- [x] Tablas/listas accionables para justificativos, planificaciones y prestamos/devoluciones.
- [x] Agregar tests frontend base para guardas por capability (`vitest` sobre `lib/capabilities`).
- [ ] Estandarizar regresion rapida de permisos por accion en vistas Admin ya migradas.
- [ ] Mantener documentacion de bootstrap alineada con el estado real.
- [ ] Ejecutar smoke manual de operaciones masivas usando endpoints batch backend nuevos.
- [x] Agregar smoke automatizado API para endpoints batch (bulk actions) y permisos base.
- [x] Agregar smoke automatizado API de permisos por rol (solo lectura vs accion) en bulk actions.
- [x] Cubrir fallos parciales API batch (IDs invalidos/no encontrados) para robustez operativa.

## Checklist Regresion Rapida De Permisos (Admin)
- [x] `App.jsx`: rutas Admin alineadas con capabilities de accion (no solo lectura).
- [x] `AdminStudentsPage.jsx`: lectura/edicion/desactivacion condicionadas por capability.
- [x] `AdminEvaluationsPage.jsx`: acceso de vista y acciones masivas alineados a `GRADE_*`.
- [x] `AdminGradesPage.jsx`: acceso de vista y eliminacion masiva alineados a `GRADE_*`.
- [x] `AdminAttendancePage.jsx`: acceso de vista y edicion masiva alineados a `CLASS_*ATTENDANCE`.
- [x] Mensajes de modo restringido presentes cuando falta capability de accion.
- [ ] Smoke manual con usuario de solo lectura (sin acciones).
- [ ] Smoke manual con usuario editor (acciones disponibles).

Nota: cobertura automatizada API completada para matriz lectura vs accion; pendiente validacion manual UX/guardas visuales en React.

## Lo Que Falta
- [x] Extender acciones masivas a Evaluaciones Admin (activar/desactivar por lote con feedback).
- [x] Extender acciones masivas a Calificaciones Admin (eliminacion por lote con feedback robusto).
- [x] Estandar basico de robustez en lotes: reintento de IDs fallidos (Evaluaciones/Calificaciones).
- [x] Homologar reintento de fallidos en todas las operaciones masivas Admin (Estudiantes/Asistencias/Evaluaciones/Calificaciones).
- [x] Definir endpoint batch backend para reducir N requests por lote.
- [ ] Completar paridad operativa Admin en modulos restantes de alto uso.
- [ ] Extender paridad operativa de roles nuevos (acciones POST faltantes y tablas de seguimiento por modulo).
- [ ] Agregar pruebas E2E o funcionales para operaciones masivas y permisos por accion.
- [ ] Agregar pruebas frontend para formularios de roles operativos (submit/errores/disabled por capability).
	- [x] Base inicial en Soporte Tecnico e Inspector Convivencia (disabled + submit con mocks).
	- [x] Extender a Psicologo, Biblioteca, Coordinador y Apoderado.
	- [x] Agregar escenarios de error backend y estados intermedios (loading/saving) por formulario.
- [ ] Cerrar checklist de migracion fase 1 React sobre API v1.
