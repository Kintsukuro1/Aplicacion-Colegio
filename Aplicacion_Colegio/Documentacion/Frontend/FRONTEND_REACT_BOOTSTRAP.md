# Frontend React Bootstrap

## Estado
Se creo una base funcional en `frontend-react/` conectada a API v1 con JWT.

## Incluye
- Login con `POST /api/v1/auth/token/`
- Refresh automatico con `POST /api/v1/auth/token/refresh/`
- Notificaciones API v1:
  - Listado: `GET /api/v1/notificaciones/`
  - Marcar leida: `POST /api/v1/notificaciones/{id}/marcar-leida/`
  - Registrar dispositivo FCM: `POST /api/v1/notificaciones/dispositivos/registrar/`
  - Desactivar dispositivo: `POST /api/v1/notificaciones/dispositivos/{id}/desactivar/`
  - Realtime SSE: `GET /api/v1/notificaciones/stream/`
  - Realtime WebSocket (Channels): `ws://<host>/ws/notificaciones/`
- Pantalla Dashboard (`/api/v1/dashboard/resumen/`)
- Pantalla Profesor Clases (`/api/v1/profesor/clases/`)
- Pantallas CRUD Profesor:
  - Asistencias: `/api/v1/profesor/asistencias/`
  - Evaluaciones: `/api/v1/profesor/evaluaciones/`
  - Calificaciones: `/api/v1/profesor/calificaciones/`
- Pantalla Estudiante Panel:
  - `/api/v1/estudiante/mi-perfil/`
  - `/api/v1/estudiante/mis-clases/`
  - `/api/v1/estudiante/mis-notas/`
  - `/api/v1/estudiante/mi-asistencia/`
- Pantalla Admin Escolar (inicial):
  - Panel: `/api/v1/dashboard/resumen/?scope=school|analytics` (resumen ejecutivo)
  - Estudiantes: `/api/v1/estudiantes/` (listado + crear + editar + desactivar, con guardas por accion, desactivacion masiva, feedback de exitos/fallos y reintento de fallidos)
    - Batch: `POST /api/v1/estudiantes/bulk-deactivate/` (`ids`) con fallback frontend a item-a-item si el endpoint no existe.
  - Cursos: `/api/v1/cursos/` (listado en modo lectura)
  - Clases: `/api/v1/profesor/clases/` (listado en modo lectura)
  - Evaluaciones: `/api/v1/profesor/evaluaciones/` (listado + seleccion por pagina + activar/desactivar en lote si existe `GRADE_EDIT`, con reintento de fallidos)
    - Batch: `POST /api/v1/profesor/evaluaciones/bulk-toggle-active/` (`ids`, `activa`) con fallback frontend a item-a-item.
  - Calificaciones: `/api/v1/profesor/calificaciones/` (listado + seleccion por pagina + eliminacion masiva si existe `GRADE_DELETE`, con reintento de fallidos)
    - Batch: `POST /api/v1/profesor/calificaciones/bulk-delete/` (`ids`) con fallback frontend a item-a-item.
  - Asistencias: `/api/v1/profesor/asistencias/` (listado con filtros + edicion masiva de estado en pagina si existe `CLASS_TAKE_ATTENDANCE`, con reintento de fallidos)
    - Batch: `POST /api/v1/profesor/asistencias/bulk-update-state/` (`ids`, `estado`) con fallback frontend a item-a-item.
- Pantallas React por rol operativo (MVP conectadas a APIs existentes):
  - Asesor Financiero (`/asesor-financiero/panel`):
    - `GET /api/asesor-financiero/dashboard/kpis/`
    - `GET /api/asesor-financiero/cuotas/estadisticas/`
    - `GET /api/asesor-financiero/becas/estadisticas/`
    - `GET /api/asesor-financiero/boletas/estadisticas/`
    - `GET /api/asesor-financiero/pagos/`
  - Inspector Convivencia (`/inspector-convivencia/panel`):
    - `GET /api/inspector/estudiantes/`
    - `POST /api/inspector/anotaciones/crear/`
    - `POST /api/inspector/justificativos/{justificativo_id}/estado/`
    - `POST /api/inspector/asistencia/registrar_atraso/`
  - Psicologo Orientador (`/psicologo-orientador/panel`):
    - `GET /api/psicologo/estudiantes/`
    - `POST /api/psicologo/entrevistas/crear/`
    - `POST /api/psicologo/derivaciones/crear/`
    - `POST /api/psicologo/derivaciones/{derivacion_id}/`
    - `POST /api/psicologo/estudiantes/{estudiante_id}/pie/`
  - Soporte Tecnico (`/soporte-tecnico/panel`):
    - `POST /api/soporte/tickets/crear/`
    - `POST /api/soporte/tickets/{ticket_id}/estado/`
    - `POST /api/soporte/usuarios/{user_id}/reset_password/` (flujo en dos fases: solicitud y ejecucion)
  - Bibliotecario Digital (`/bibliotecario-digital/panel`):
    - `GET /api/bibliotecario/recursos/`
    - `GET /api/bibliotecario/usuarios/`
    - `POST /api/bibliotecario/recursos/crear/`
    - `POST /api/bibliotecario/recursos/{recurso_id}/publicar/`
    - `POST /api/bibliotecario/prestamos/crear/`
    - `POST /api/bibliotecario/prestamos/{prestamo_id}/devolver/`
  - Coordinador Academico (`/coordinador-academico/panel`):
    - `POST /api/coordinador/planificaciones/{planificacion_id}/estado/`
  - Apoderado (`/apoderado/panel`):
    - `GET /api/apoderado/justificativos/`
    - `GET /api/apoderado/firmas/`
    - `POST /api/apoderado/firmas/firmar/`
- Guardas de rutas por capabilities usando `GET /api/v1/auth/me/`
  - El menu lateral muestra solo rutas autorizadas
  - Si el usuario entra manualmente a una ruta sin permisos, ve "Acceso Denegado"
  - Rutas Admin de evaluaciones/calificaciones/asistencias permiten acceso tambien por capabilities de accion (create/edit/delete/take), no solo de lectura.
  - Se agregaron rutas protegidas para roles operativos (finanzas, convivencia, psicologia, soporte, biblioteca, coordinacion, apoderado) con `anyOf` de capabilities alineadas al backend.
- Guardas por accion en CRUD Profesor:
  - Asistencias: crear/editar/eliminar solo con `CLASS_TAKE_ATTENDANCE`
  - Evaluaciones/Calificaciones: controles separados por `GRADE_CREATE`, `GRADE_EDIT`, `GRADE_DELETE`
- Filtros persistentes por URL (query params):
  - Dashboard y Admin Panel conservan `scope`
  - Admin Asistencias conserva `clase_id` y `fecha`
- Paginacion servidor (DRF) en vistas Admin con `page` en URL:
  - Estudiantes, Cursos, Clases, Evaluaciones, Calificaciones, Asistencias

## Setup
1. Copiar `frontend-react/.env.example` a `frontend-react/.env`.
2. Ajustar `VITE_API_BASE_URL` (por defecto `http://127.0.0.1:8000`).
3. Ejecutar en `frontend-react/`:
   - `npm install`
   - `npm run dev`

## Notas de Integracion
- Si backend usa CORS por origen, incluir `http://localhost:5173` en `API_ALLOWED_ORIGINS`.
- El contrato dashboard consumido es el documentado en `docs/API_CONTRACT_DASHBOARD_V1.md`.
- Smoke automatizado API disponible en `tests/unit/api/test_v1_bulk_actions.py`:
  - Valida endpoints batch (estudiantes/asistencias/evaluaciones/calificaciones).
  - Incluye matriz de permisos por rol: usuario con capabilities de lectura puede listar pero recibe `403` en acciones bulk de edicion/eliminacion.
  - Incluye robustez de fallos parciales: mezcla de IDs validos e invalidos con retorno `success/failed/failed_ids` consistente.
- Smoke automatizado frontend disponible en `frontend-react/src/lib/capabilities.test.js`:
  - Ejecutable con `npm run test:run` en `frontend-react/`.
  - Cubre helpers `hasCapability`, `hasAnyCapability`, `hasAllCapabilities`, `isSystemAdmin` y `canAccessRoute`.
  - Verifica reglas `anyOf/allOf` y override de `SYSTEM_ADMIN` para rutas protegidas.
- Pruebas de componentes frontend disponibles para formularios de roles:
  - `frontend-react/src/features/soporte_tecnico/SoporteTecnicoPage.test.jsx`
  - `frontend-react/src/features/inspector_convivencia/InspectorConvivenciaPage.test.jsx`
  - `frontend-react/src/features/psicologo_orientador/PsicologoOrientadorPage.test.jsx`
  - `frontend-react/src/features/bibliotecario_digital/BibliotecarioDigitalPage.test.jsx`
  - `frontend-react/src/features/coordinador_academico/CoordinadorAcademicoPage.test.jsx`
  - `frontend-react/src/features/apoderado/ApoderadoPage.test.jsx`
  - Cobertura actual: estado disabled por falta de capability, carga inicial, submit exitoso, manejo de errores backend y estados intermedios `loading/saving` con `apiClient` mockeado.
  - Estado validado: `npm run test:run` => 35 tests passing.

- Mejoras UX en acciones por ID (reduccion de entrada manual):
  - Inspector Convivencia: selector de clase para registrar atraso (usa `GET /api/v1/profesor/clases/` con fallback seguro a lista vacia).
  - Inspector Convivencia: lista de justificativos pendientes con acciones rápidas (`Aprobar`, `Rechazar`, `Usar en formulario`) usando `GET /api/inspector/justificativos/`.
  - Bibliotecario Digital: selector de recurso para publicar/despublicar (reusa recursos cargados).
  - Bibliotecario Digital: lista de préstamos activos con acciones rápidas (`Devolver ahora`, `Usar en formulario`) usando `GET /api/bibliotecario/prestamos/`.
  - Coordinador Académico: lista de planificaciones pendientes con acciones rápidas (`Aprobar`, `Rechazar`, `Usar en formulario`) usando `GET /api/coordinador/planificaciones/`.
  - Soporte Tecnico: autocompleta `ticket_id` tras crear ticket y `approval_request_id` tras generar solicitud de reset.

## Siguiente Paso Recomendado
- Cerrar UX de seleccion/listado para acciones por ID (tablas con acciones inline y no solo formularios por ID manual).
- Agregar pruebas frontend (Vitest/RTL) para guardas de rutas y formularios de acciones por capability.
