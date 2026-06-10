# Revision Django - Mejoras y deuda tecnica

Fecha: 2026-05-09  
Alcance: `Aplicacion_Colegio/backend`, API v1, vistas legacy Django, servicios, settings, multi-tenant, seguridad y usabilidad operativa.

## Resumen ejecutivo

El backend Django ya tiene una base potente: separacion por apps, capa API v1, capabilities, middleware tenant, auditoria, seguridad, pagos, import/export y una suite de pruebas amplia. El mayor riesgo no esta en falta de funcionalidad, sino en la convivencia de dos generaciones de codigo: vistas legacy en `backend/apps/core/views` y API v1 en `backend/apps/api`. Esa convivencia genera duplicacion, permisos repetidos, filtros tenant inconsistentes y mas superficie para errores pequenos como el `Count('id')` reciente en dashboard.

La recomendacion principal es estabilizar una "columna vertebral" Django: contrato unico para tenant/permisos, errores API, paginacion, logging y servicios de negocio. Luego migrar por modulos desde las vistas legacy hacia API v1, dejando aliases temporales solo documentados.

## Validaciones ejecutadas

- `python manage.py check --deploy`
- `python manage.py show_urls`
- Busqueda estatica de `TODO`, `except Exception`, permisos, endpoints publicos, settings, tenant y archivos grandes.
- Revision manual de archivos representativos:
  - `backend/apps/core/settings.py`
  - `backend/common/tenancy.py`
  - `backend/apps/core/middleware/tenant.py`
  - `backend/apps/api/base.py`
  - `backend/apps/api/helpers.py`
  - `backend/apps/api/permissions.py`
  - `backend/apps/api/resources_views.py`
  - `backend/apps/api/domain_views.py`
  - `backend/apps/api/payment_views.py`
  - `backend/apps/api/upload_views.py`
  - `backend/apps/api/seguridad_views.py`

## Hallazgos criticos

### 1. TenantMiddleware no reconoce `colegio_id`

Archivo: `backend/apps/core/middleware/tenant.py`  
El middleware bloquea parametros cross-colegio para `rbd`, `rbd_colegio`, `escuela_rbd` y `colegio`, pero no incluye `colegio_id`. La API v1 usa mucho `colegio_id`, por ejemplo dashboard, reportes y endpoints academicos. Esto puede dejar validaciones cross-tenant dependiendo de cada vista, en vez de una barrera central.

Accion recomendada:
- Agregar `colegio_id` a `SCHOOL_PARAM_KEYS`.
- Cubrir con test de middleware para usuario no global usando `?colegio_id=<otro_rbd>`.
- Revisar tambien nombres como `colegio_rbd` porque pagos usa ese parametro.

Prioridad: Alta.

### 2. Produccion no esta endurecida por defecto

`manage.py check --deploy` reporta:
- `SECURE_HSTS_SECONDS` sin configurar.
- `SECURE_SSL_REDIRECT` no activo.
- `SESSION_COOKIE_SECURE = False`.
- `CSRF_COOKIE_SECURE = False`.

Archivo: `backend/apps/core/settings.py`

Accion recomendada:
- Mover esos flags a variables de entorno con defaults seguros cuando `DEBUG=False`.
- Agregar una seccion `production.py` o settings por entorno.
- Documentar valores esperados para deploy.

Prioridad: Alta antes de produccion real.

### 3. Admin global puede elegir colegios en vistas, pero no hay politica central unica

Actualmente algunas vistas aceptan `colegio_id`, otras `colegio_rbd`, otras `escuela_rbd`, otras resuelven por subdominio o `request.user.rbd_colegio`. Esto funciona mientras cada endpoint lo hace bien, pero cuesta mantener y facilita regresiones.

Accion recomendada:
- Crear un helper unico tipo `resolve_school_scope(request, allow_global=True, param_names=('colegio_id', 'colegio_rbd', ...))`.
- Devolver siempre un objeto con `school_id`, `is_global`, `requested_school_id`, `source`.
- Usarlo en dashboard, reportes, pagos, calendario, import/export y finanzas.

Prioridad: Alta.

### 4. Muchos `except Exception` silenciosos

Hay muchos bloques `except Exception` en servicios y vistas. Algunos son razonables como fallback, pero varios esconden bugs reales y devuelven ceros o estados vacios. El caso reciente de dashboard ejecutivo es un ejemplo: un error ORM termino como fallback visual en React.

Archivos con mayor riesgo:
- `backend/apps/core/views/**`
- `backend/apps/core/services/**`
- `backend/apps/api/services/dashboard_analytics_service.py`
- `backend/apps/api/payment_views.py`
- `backend/apps/academico/services/grades_service.py`
- `backend/apps/academico/services/attendance_service.py`

Accion recomendada:
- Cambiar `except Exception: pass` por excepciones concretas.
- Loggear con `logger.exception` cuando el resultado afecta datos de usuario.
- Agregar tests para payloads vacios por error vs datos realmente vacios.

Prioridad: Alta en dashboards, pagos, seguridad y reportes.

## Cosas que hay que hacer funcionar mejor

### Dashboard y analitica

Estado actual:
- Hay dos mundos: dashboard legacy en `core/services/dashboard_*` y dashboard API v1 en `api/services/dashboard_*`.
- Los nombres de metricas no siempre coinciden entre summary, executive y frontend.
- La cache usa scope/colegio/usuario, pero cuando se agregan nuevos filtros hay que recordar incluirlos en key.

Mejoras:
- Definir contrato unico `DashboardPayload v1` con campos obligatorios por scope.
- Agregar tests para:
  - admin escolar: `school`, `analytics`.
  - admin general: `global`, `school` agregado, `school` con `colegio_id`.
  - usuario sin colegio.
  - cache invalidada al cambiar datos academicos relevantes.
- Evitar que errores de backend se traduzcan en ceros silenciosos.

### Pagos y suscripciones

Estado actual:
- `payment_views.py` concentra demasiados casos: planes, checkout, historial, transferencias, exportacion, aprobacion, upgrade, cancelacion, renovacion y webhook.
- Varias funciones aceptan `colegio_rbd` en request. Para admin global esta bien; para usuario normal deberia validarse siempre contra su colegio.
- Webhook permite `AllowAny`, correcto para proveedores, pero si no hay `PAYMENT_WEBHOOK_SECRET` ni `PAYMENT_WEBHOOK_TOKEN`, el endpoint queda aceptando eventos sin firma.

Mejoras:
- Separar en `plans_views.py`, `checkout_views.py`, `transfer_views.py`, `subscription_views.py`, `webhook_views.py`.
- En startup/deploy, fallar o advertir fuerte si webhook no tiene secreto en `DEBUG=False`.
- Testear usuario normal intentando pagar/modificar otro `colegio_rbd`.
- Estandarizar el nombre del parametro: `colegio_id` o `colegio_rbd`, pero no ambos sin helper.

### Importacion/exportacion

Estado actual:
- Hay endpoints legacy y v1 alias.
- Se maneja bastante logica de validacion en views.

Mejoras:
- Mover validaciones de CSV/Excel a servicios puros.
- Devolver previsualizacion antes de importar.
- Agregar reporte de errores por fila descargable.
- Agregar job async para importaciones grandes, con estado consultable.

### Seguridad y sesiones

Estado actual:
- Hay endpoints utiles para sesiones, auditoria y desbloqueo.
- Algunos endpoints devuelven listas cortadas a 100/200/300 sin paginacion estandar.
- `revoke_session` depende de `ActiveSession.revoke_session`; conviene verificar que un admin escolar no pueda revocar sesiones de otro colegio.

Mejoras:
- Usar paginacion DRF en auditoria, sesiones y password history.
- Agregar filtro por colegio para admin global.
- Agregar tests explicitos de revocacion cross-school.
- En `change_password_secure`, invalidar/rotar sesiones existentes tras cambiar password.

### Uploads

Estado actual:
- `upload_image` valida MIME declarado, comprime y limita tamano.
- Falta verificar contenido real contra MIME y manejar imagenes potencialmente muy grandes en pixeles antes de procesar.

Mejoras:
- Validar `Image.verify()` o formato real antes de comprimir.
- Definir limite de megapixeles.
- Considerar storage privado para documentos sensibles.
- Registrar auditoria si el upload se asocia a datos personales.

## Overcoding y simplificacion

### 1. Servicios demasiado grandes

Archivos grandes detectados:
- `dashboard_context_service.py`: 1341 lineas.
- `grades_service.py`: 1311 lineas.
- `dashboard_admin_service.py`: 1027 lineas.
- `student_service.py`: 874 lineas.
- `accounts/models.py`: 857 lineas.
- `academico/models.py`: 837 lineas.
- `academic_reports_service.py`: 774 lineas.
- `resources_views.py`: 739 lineas.

Riesgo:
- Alta carga cognitiva.
- Dificil aislar tests.
- Cambios pequenos pueden tocar mucho contexto.

Mejora:
- Separar por caso de uso. Ejemplo para calificaciones:
  - `grade_entry_service.py`
  - `grade_summary_service.py`
  - `grade_validation_service.py`
  - `grade_export_service.py`
- Evitar clases "Dios" de dashboard. Crear builders pequenos por rol/scope.

### 2. Duplicacion de servicios legacy vs API

Ejemplos:
- `backend/apps/core/services/apoderado_api_service.py`
- `backend/apps/api/services/apoderado_api_service.py`
- `backend/apps/core/services/estudiante_api_service.py`
- `backend/apps/api/services/student_api_service.py`
- multiples `dashboard_*`.

Mejora:
- Elegir una capa de servicios canonica.
- API v1 y legacy deberian llamar a los mismos servicios de dominio, no mantener logicas paralelas.
- Marcar servicios legacy con deprecation interna.

### 3. Comentarios y banners excesivos

Hay archivos con banners grandes, comentarios de fase y textos de migracion. Ayudan historicamente, pero hoy hacen mas dificil leer lo importante.

Mejora:
- Mover historia de migracion a docs.
- Mantener en codigo solo comentarios que expliquen reglas de negocio no obvias.

## Usabilidad backend/API

### 1. Respuestas de error inconsistentes

Se mezclan:
- `{'detail': '...'}`.
- `{'error': '...'}`.
- listas de errores de serializer.
- excepciones Django/DRF directas.

Mejora:
- Definir formato estandar:
  ```json
  {
    "detail": "Mensaje humano",
    "code": "ERROR_CODE",
    "fields": {}
  }
  ```
- Crear helper comun para errores de negocio.
- Mantener mensajes pensados para UI, no solo para desarrolladores.

### 2. Paginacion inconsistente

DRF tiene paginacion por defecto, pero varias funciones manuales devuelven listas cortadas con `[:100]`, `[:200]`, `[:300]`.

Mejora:
- Convertir endpoints de listas manuales a `GenericAPIView` o ViewSet paginado.
- Exponer `count`, `next`, `previous`, `results`.

### 3. Filtros y busquedas no uniformes

Hay helpers como `apply_search_filter`, pero no esta aplicado en todos los modulos.

Mejora:
- Estandarizar query params: `search`, `ordering`, `page_size`, `colegio_id`, `from`, `to`, `estado`.
- Documentarlo en `docs/API_CONTRACT_MOBILE_MVP_V1.md` o similar.

## Multi-tenant y permisos

### Lo bueno

- Existe `TenantManager`.
- Existe `TenantMiddleware`.
- Existe `PolicyService` y `HasCapability`.
- Hay tests de aislamiento tenant.

### Riesgos

- `TenantManager.objects` sin tenant activo devuelve todos los colegios/datos. Eso es util en scripts, pero peligroso si una vista olvida setear tenant o filtro manual.
- Algunos endpoints con `IsAuthenticated` no tienen capabilities especificas y resuelven permisos dentro de la funcion.
- Admin global y subdominio tenant pueden interactuar de forma sutil: si entra por subdominio, el tenant context puede filtrar managers aunque el admin global espere ver todo.

Mejoras:
- Linter/test que detecte ViewSets con `IsAuthenticated` sin `HasCapability` salvo lista permitida.
- Test que haga request real a API v1 con usuario escolar y `colegio_id` ajeno.
- Helper unico para "global con colegio seleccionado".
- Documentar reglas:
  - usuario escolar nunca puede pedir otro colegio;
  - admin global puede pedir todos o uno;
  - admin global en subdominio puede operar en ese colegio salvo `scope=global`.

## Performance

### Riesgos vistos

- Dashboards y reportes tienen muchas queries agregadas, algunas repetidas por seccion.
- Muchas listas manuales no usan paginacion.
- Hay `select_related`/`prefetch_related`, pero no siempre en endpoints legacy.
- Cache de dashboard existe, pero requiere invalidacion fina.

Mejoras:
- Agregar tests de numero de queries para endpoints mas usados:
  - dashboard resumen;
  - dashboard executive;
  - listado estudiantes;
  - clases profesor;
  - notas estudiante/apoderado;
  - finanzas dashboard.
- Agregar `django-debug-toolbar` solo local y `assertNumQueries` en tests criticos.
- Para reportes pesados, usar jobs async y tabla de resultados/exportaciones.

## Seguridad

### Puntos positivos

- JWT con refresh rotation.
- Django Axes.
- Validadores fuertes de password.
- Auditoria y sesiones activas.
- Uploads restringidos por extension/MIME.
- Capabilities por rol.

### Mejoras concretas

- Produccion: activar cookies secure, HSTS, SSL redirect.
- Webhook: exigir firma/token cuando `DEBUG=False`.
- Upload: validar contenido real y megapixeles.
- Rate limiting especifico para login/onboarding/webhook/upload.
- Sanitizar logs para no guardar datos sensibles en excepciones.
- Revisar `AllowAny` publicos:
  - planes y proveedores: ok.
  - onboarding register/check slug: ok con throttle.
  - webhook: solo ok con firma obligatoria.

## Pruebas recomendadas

Agregar o reforzar:

1. Tenant middleware:
   - bloquea `colegio_id`, `colegio_rbd`, `rbd`, `escuela_rbd` ajenos.
   - admin global puede usar `colegio_id`.

2. Dashboard:
   - admin general `school` agregado vs `school&colegio_id`.
   - executive no devuelve ceros por excepcion silenciosa.
   - cache key incluye colegio seleccionado.

3. Pagos:
   - admin escolar no puede checkout/upgrade/cancelar otro colegio.
   - webhook sin firma falla en produccion.
   - transferencia aprobada solo por usuario autorizado.

4. Seguridad:
   - admin escolar no revoca sesiones de otro colegio.
   - password change invalida sesiones anteriores.

5. Upload:
   - MIME falso falla.
   - imagen enorme en pixeles falla.
   - archivo no imagen con extension imagen falla.

## Roadmap propuesto

### Semana 1: seguridad y tenant

- Agregar `colegio_id` y `colegio_rbd` a `TenantMiddleware.SCHOOL_PARAM_KEYS`.
- Crear `resolve_school_scope`.
- Endurecer settings por entorno.
- Hacer obligatorio `PAYMENT_WEBHOOK_SECRET` o token en produccion.

### Semana 2: contratos API

- Estandarizar errores.
- Estandarizar paginacion en endpoints manuales principales.
- Documentar parametros comunes.
- Agregar tests de permisos en API v1.

### Semana 3: dashboard y reportes

- Consolidar builders de dashboard.
- Cubrir scopes con tests.
- Agregar invalidacion de cache o versionado por modulo.
- Medir queries y optimizar N+1.

### Semana 4: reducir duplicacion

- Elegir servicios canonicos por dominio.
- Marcar servicios legacy.
- Migrar vistas legacy de roles a services/API compartidos.
- Dividir servicios grandes.

## Checklist accionable corto

- [ ] Incluir `colegio_id` y `colegio_rbd` en `TenantMiddleware`.
- [ ] Crear helper `resolve_school_scope`.
- [ ] Activar settings seguros cuando `DEBUG=False`.
- [ ] Exigir firma en `payment_webhook` en produccion.
- [ ] Reemplazar `except Exception: pass` en dashboards/reportes/pagos.
- [ ] Paginacion estandar para seguridad, auditoria y listas manuales.
- [ ] Tests cross-tenant por API real.
- [ ] Tests de dashboard admin general con colegio seleccionado.
- [ ] Tests de uploads con MIME falso.
- [ ] Dividir `grades_service.py` y `dashboard_context_service.py`.

## Nota final

El sistema no necesita una reescritura grande. Lo que mas valor daria es una limpieza orientada a contratos: una forma unica de resolver colegio, una forma unica de verificar permisos, una forma unica de devolver errores y una forma unica de paginar. Con eso, las funcionalidades existentes quedan mucho mas faciles de mantener y los bugs dejan de esconderse detras de fallbacks silenciosos.
