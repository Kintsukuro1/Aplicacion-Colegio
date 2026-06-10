# API Contract Mobile MVP v1

Fecha: 2026-03-16
Version: 1.0.0
Ambito: Fase 2 del roadmap (app movil consumiendo API v1)

## Objetivo
Definir un contrato minimo y estable para que una app movil (React Native o Flutter) pueda operar en produccion inicial sin depender de templates web.

## Reglas de seguridad
- Todas las rutas privadas requieren JWT valido.
- Todas las rutas deben respetar aislamiento tenant por colegio.
- No exponer datos de otro colegio aunque el cliente envie filtros manuales.
- Permisos sensibles se validan por capability, no por nombre de rol.

## Base URL
- Prefijo versionado: /api/v1/

## Endpoints Mobile MVP

### 1) Auth
- POST /api/v1/auth/token/
  - Uso: login inicial y obtencion de access/refresh.
  - Request minimo:
    - email
    - password
  - Response minimo:
    - access
    - refresh

- POST /api/v1/auth/token/refresh/
  - Uso: renovar access token.

- POST /api/v1/auth/token/verify/
  - Uso: verificar validez de token.

- POST /api/v1/auth/logout/
  - Uso: invalidar sesion (refresh).

- GET /api/v1/auth/me/
  - Uso: bootstrap de identidad del usuario autenticado.

### 2) Dashboard
- GET /api/v1/dashboard/resumen/?scope=auto|self|school|analytics|global
  - Uso: pintar home por rol.
  - Capability esperada: DASHBOARD_VIEW_SELF o superiores segun scope.

### 3) Estudiante (mobile)
- GET /api/v1/estudiante/mi-perfil/
- GET /api/v1/estudiante/mis-clases/
- GET /api/v1/estudiante/mis-notas/
- GET /api/v1/estudiante/mi-asistencia/

### 4) Apoderado (mobile)
- GET /api/v1/apoderado/mis-pupilos/
- GET /api/v1/apoderado/pupilo/{student_id}/notas/
- GET /api/v1/apoderado/pupilo/{student_id}/asistencia/
- GET /api/v1/apoderado/pupilo/{student_id}/anotaciones/
- GET /api/v1/apoderado/comunicados/
- GET /api/v1/apoderado/pagos/estado/
- POST /api/v1/apoderado/justificativos/

### 5) Profesor (mobile minimo)
- GET /api/v1/profesor/clases/
- GET /api/v1/profesor/asistencias/
- GET /api/v1/profesor/evaluaciones/
- GET /api/v1/profesor/calificaciones/

Nota:
Las rutas de libro de clases y reportes normativos implementadas en vistas web deben exponerse en API v1 o mantenerse tras un BFF movil antes del release de app.

### 6) Notificaciones
- GET /api/v1/notificaciones/
- GET /api/v1/notificaciones/resumen/
- POST /api/v1/notificaciones/marcar-todas-leidas/
- POST /api/v1/notificaciones/{notification_id}/marcar-leida/
- POST /api/v1/notificaciones/dispositivos/registrar/
- POST /api/v1/notificaciones/dispositivos/{device_id}/desactivar/

## Contrato de errores
- 400: request invalido o parametros invalidos.
- 401: no autenticado / token invalido.
- 403: autenticado sin capability requerida.
- 404: recurso inexistente o fuera de alcance tenant.
- 500: error interno (sin filtrar informacion sensible).

## Criterios de aceptacion Mobile MVP
1. Login, refresh y me funcionales en iOS y Android.
2. Dashboard resumen responde con scope auto por defecto.
3. Estudiante y apoderado pueden completar flujo diario sin fallback web.
4. Notificaciones push/web operan con registro de dispositivo.
5. Suite smoke API por rol pasa local y en CI.

## Pruebas recomendadas (smoke)
- auth: token obtain/refresh/verify/logout/me.
- dashboard: scope auto y rechazo por capability.
- estudiante: perfil, clases, notas, asistencia.
- apoderado: pupilos + notas/asistencia/anotaciones de un pupilo permitido.
- notificaciones: listar, resumen, marcar leida, registrar dispositivo.

Estado actual:
- Implementado smoke matrix inicial en tests/integration/api_mobile/test_mobile_mvp_smoke.py.
- Nota de ejecución: la suite se auto-salta si /api/v1 no está expuesta en la fuente única (root), dejando visible el bloqueo de integración para Fase 2.

## Riesgos abiertos
- Coexistencia raiz vs carpeta anidada para endpoints API puede generar diferencias de despliegue.
- Algunas funcionalidades clave del modulo profesor siguen acopladas a templates y requieren exposicion API v1 dedicada.
- Mantener contrato estable mientras se avanza con fases 3-5.

## Siguiente entrega tecnica
Crear matriz de pruebas smoke para este contrato en tests/integration/api_mobile/ con cobertura minima por rol.