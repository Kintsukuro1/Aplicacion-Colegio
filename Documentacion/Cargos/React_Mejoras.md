# Revision React - Mejoras y deuda tecnica

Fecha: 2026-05-09  
Alcance revisado: `Aplicacion_Colegio/frontend-react`

## Resumen ejecutivo

La aplicacion React ya tiene una base funcional razonable: Vite, React Router, React Query, Zustand, code splitting por paginas, tests con Vitest y una separacion inicial por `features`. El build de produccion compila correctamente.

Los riesgos principales no estan en que "no exista frontend", sino en consistencia y mantenibilidad: hay doble configuracion de React Query, paginas grandes con demasiada responsabilidad, errores visuales por texto con encoding roto, manejo de sesion basado en `localStorage`, pruebas que no terminan de forma estable y una mezcla de hooks propios con React Query que duplica patrones de carga.

Prioridades recomendadas:

1. Corregir configuracion global: un solo `QueryClientProvider`, una sola politica de cache/retry y Devtools solo en desarrollo.
2. Reparar encoding de textos visibles y comentarios, porque afecta login, metadatos, PWA y documentacion interna.
3. Estabilizar `npm run test:run`, que durante la revision quedo colgado hasta timeout.
4. Reducir complejidad de paginas grandes separando hooks de datos, formularios, tablas y acciones.
5. Unificar manejo de errores, permisos, tenant, paginacion y feedback al usuario.

## Validaciones ejecutadas

Comandos ejecutados desde `Aplicacion_Colegio/frontend-react`:

```powershell
npm run build
npm run test:run
```

Resultado:

- `npm run build`: exitoso. Vite compilo 515 modulos y genero `dist/`.
- `npm run test:run`: no termino dentro de 124 segundos. Quedaron procesos `node` de Vitest/Tinypool vivos y se cerraron solo esos procesos de prueba. Esto sugiere tests colgados, workers sin cerrar, mocks incompletos o algun efecto asincrono que no libera recursos.

No se encontro script de lint en `package.json`.

## Hallazgos criticos

### 1. Doble `QueryClientProvider` y doble `QueryClient`

Archivos:

- `src/main.jsx`
- `src/App.jsx`
- `src/lib/queryClient.js`

`main.jsx` envuelve la app con `QueryClientProvider` usando `queryClient` desde `src/lib/queryClient.js`, pero `App.jsx` crea otro `new QueryClient()` y vuelve a envolver toda la aplicacion.

Impacto:

- Las politicas reales de cache/retry pueden no ser las esperadas.
- Devtools puede estar mirando un cliente distinto al que usan algunos componentes.
- Se pierde claridad sobre invalidaciones y estado compartido.

Recomendacion:

- Eliminar el `QueryClientProvider` de `App.jsx`.
- Usar solamente el `queryClient` central de `src/lib/queryClient.js`.
- Renderizar `ReactQueryDevtools` solo si `import.meta.env.DEV`.

### 2. Tests colgados en la corrida completa

`npm run test:run` no finalizo dentro del timeout.

Impacto:

- No se puede confiar en CI como puerta de calidad.
- Los cambios pequenos pueden quedar sin validacion automatica real.
- Puede haber timers, listeners, promises o mocks de `fetch`/router que no se limpian.

Recomendacion:

- Ejecutar por grupos hasta encontrar el archivo que cuelga:

```powershell
npx vitest run src/features/dashboard/DashboardPage.test.jsx
npx vitest run src/components/ProtectedRoute.test.jsx
npx vitest run --pool=forks --reporter=verbose
```

- Revisar tests con `setTimeout`, `waitFor`, service worker, React Query retries o fetch mocks no resueltos.
- En `setupTests`, limpiar QueryClient, timers y mocks despues de cada test.

### 3. Textos con encoding roto

Se observaron textos visibles y comentarios con caracteres rotos en:

- `src/App.jsx`
- `src/features/auth/LoginPage.jsx`
- `src/styles.css`
- `src/components/UpdateListener.jsx`
- `index.html`
- varios documentos `FASE*.md`

Ejemplos afectados: textos de login, descripcion meta, titulo, comentarios de CSS, mensajes PWA y placeholders.

Impacto:

- Mala experiencia visual.
- Sensacion de producto no pulido.
- Puede afectar accesibilidad si lectores de pantalla pronuncian texto corrupto.

Recomendacion:

- Normalizar archivos a UTF-8.
- Corregir textos visibles primero: login, dashboard, botones, errores, metadatos y toasts.
- Evitar copiar texto desde fuentes con codificacion distinta sin revisar diff.

### 4. Sesion basada en `localStorage`

Archivo:

- `src/lib/authStore.js`

Los access/refresh tokens se guardan en `localStorage`.

Impacto:

- Mayor exposicion ante XSS.
- Logout remoto y refresh pueden quedar en estados ambiguos si una pestana falla.

Recomendacion:

- Para produccion, evaluar cookies `HttpOnly`, `Secure`, `SameSite` desde Django.
- Si se mantiene `localStorage`, reforzar CSP, sanitizacion, expiracion local y limpieza multi-tab con evento `storage`.

### 5. Tenant se carga antes de conocer al usuario

Archivo:

- `src/lib/tenantContext.js`

El tenant se resuelve por subdominio o `VITE_TENANT_RBD`, no por el usuario autenticado. Para `admin_general`, esto puede chocar con vistas globales o seleccion de colegio.

Impacto:

- Branding o contexto escolar incorrecto para usuarios globales.
- La seleccion de colegio en dashboard puede no sincronizarse con el contexto general de la app.

Recomendacion:

- Distinguir `tenant visual` de `scope de datos`.
- Para admin general, permitir estado "sin colegio seleccionado" y exponer selector global cuando corresponda.
- Persistir colegio seleccionado de forma explicita, no como efecto lateral del tenant.

## Cosas que conviene hacer funcionar mejor

### Dashboard

Archivo principal:

- `src/features/dashboard/DashboardPage.jsx`

El dashboard ya maneja `scope=analytics`, `scope=global`, `scope=school` y seleccion de colegio para admin general, pero concentra fetches, UI, transformaciones y vistas en un solo archivo.

Mejoras:

- Extraer hooks:
  - `useDashboardResumen(scope, colegioId)`
  - `useDashboardExecutive(scope, colegioId)`
  - `useDashboardSchools(enabled)`
- Separar componentes:
  - `DashboardScopeTabs`
  - `SchoolSelector`
  - `DashboardErrorBanner`
  - `ExecutiveMetricsGrid`
- Mostrar estado especifico cuando no hay colegio seleccionado en `school`: agregado global vs colegio concreto.
- Evitar banners repetidos de error ejecutivo si el resumen ya trae informacion suficiente.

### Login y registro

Archivos:

- `src/features/auth/LoginPage.jsx`
- `src/features/auth/RegisterPage.jsx`

Mejoras:

- Corregir encoding.
- Usar `Link` de React Router en vez de `<a href="/register">` para evitar recarga completa.
- Mostrar estado de tenant cargando si el logo/nombre depende de tenant.
- Mejorar mensajes de credenciales invalidas sin filtrar detalles sensibles.

### Pagos y suscripciones

Archivos:

- `src/features/subscriptions/PricingPage.jsx`
- `src/features/subscriptions/PaymentHistoryPage.jsx`
- `src/features/subscriptions/TransferNoticesPage.jsx`
- `src/features/subscriptions/SubscriptionDashboard.jsx`

Mejoras:

- Reemplazar `alert()` por `Toast` o modales consistentes.
- Mostrar estados claros de "procesando pago", "redireccionando" y "fallo recuperable".
- Unificar copy de errores backend.
- Validar que acciones financieras pidan confirmacion si son irreversibles.

### Asistencias

Archivo:

- `src/features/admin_escolar/AdminAttendancePage.jsx`

El archivo tiene mas de 500 lineas y mezcla filtros, query params, formulario, paginacion, seleccion masiva, fallback de endpoint batch y render.

Mejoras:

- Extraer hook `useAttendanceFilters`.
- Extraer hook `useAttendanceBulkActions`.
- Extraer tabla y formulario.
- Revisar paginacion: el calculo de `hasNext` usa `pagination.currentPage < Math.max(0, pagination.totalPages - 1)`, que sugiere indices base 0 en frontend. Si backend usa paginas base 1, puede producir deshabilitados incorrectos.

### PWA / Service Worker

Archivos:

- `src/main.jsx`
- `src/components/UpdateListener.jsx`
- `public/sw.js`

Mejoras:

- Devtools/logs solo en desarrollo o bajo flag.
- El toast de nueva version no parece ofrecer boton visible de recarga inmediata, aunque el comentario habla de "dismiss + reload options".
- Revisar que el cleanup del timer se ejecute correctamente: retornar una funcion dentro del handler de mensaje no limpia el efecto principal.

## Overcoding y deuda de estructura

### Paginas demasiado grandes

Archivos con mayor complejidad aproximada:

- `AdminAttendancePage.jsx`: 515 lineas.
- `AdminStudentsPage.jsx`: 452 lineas.
- `CalendarEventsPage.jsx`: 439 lineas.
- `BibliotecarioDigitalPage.jsx`: 437 lineas.
- `PsicologoOrientadorPage.jsx`: 437 lineas.
- `AdminGradesPage.jsx`: 431 lineas.
- `DashboardPage.jsx`: 413 lineas.
- `InspectorConvivenciaPage.jsx`: 406 lineas.

Patron repetido:

- Estados locales extensos.
- Fetch manual o hooks mezclados.
- Transformacion de payloads dentro del componente.
- Formularios y tablas en el mismo archivo.
- Logica de permisos dentro del render.

Recomendacion:

- Mantener cada page como orquestador.
- Mover datos a hooks.
- Mover formularios/tablas a componentes locales de la feature.
- Crear helpers de normalizacion por dominio cuando el backend tenga variantes de nombres.

### Hooks propios y React Query conviven sin frontera clara

Archivos:

- `src/lib/hooks/useFetch.js`
- `src/lib/hooks/usePagination.js`
- paginas que usan `useQuery`

Hay dos estilos de carga: React Query y hooks propios con `useState/useEffect`. Esto aumenta bugs de cache, reintentos, loading y refetch.

Recomendacion:

- Usar React Query para consultas remotas nuevas.
- Mantener hooks propios solo como wrappers de `useQuery`, no como mecanismo paralelo.
- Centralizar keys de query por modulo.

### Documentos y ejemplos dentro de `src`

Se encontraron documentos y ejemplos tipo fase dentro de `src/components` y `src/lib/hooks`.

Impacto:

- Ruido para busquedas.
- Riesgo de importar ejemplos por accidente.
- Dificulta distinguir producto real de material de referencia.

Recomendacion:

- Mover guias y ejemplos a `Documentacion/` o `docs/`.
- Dejar en `src` solo codigo de runtime y tests.

## Usabilidad

### Errores y feedback

Problemas:

- Algunos componentes usan banners.
- Otros usan `Toast`.
- Otros usan `alert()`.
- Algunos `catch` descartan detalles.

Mejoras:

- Definir un patron:
  - Error recuperable de formulario: inline.
  - Error de carga de pagina: empty state con boton reintentar.
  - Accion exitosa: toast.
  - Accion destructiva: modal de confirmacion.
- El `apiClient` deberia exponer un error normalizado con `message`, `fieldErrors`, `status`, `code`.

### Navegacion y permisos

Archivo:

- `src/App.jsx`

`APP_ROUTES` esta dentro de `App.jsx` con rutas, labels, roles, capabilities y componentes lazy.

Mejoras:

- Mover rutas a `src/routes/appRoutes.js`.
- Usar ese mismo contrato para sidebar, mobile nav, breadcrumbs y tests.
- Agregar prueba que valide que cada ruta visible tiene label, componente y regla de acceso.

### Mobile

Archivos:

- `src/components/MobileBottomNav.jsx`
- `src/components/AppSidebar.jsx`
- `src/styles.css`

Mejoras:

- Revisar que la navegacion inferior no tape botones o tablas.
- Verificar dashboards y tablas con viewport movil real.
- Agregar estados vacios compactos y acciones principales visibles.

### Accesibilidad

Mejoras:

- Revisar labels asociados con `htmlFor`/`id` en formularios complejos.
- Evitar iconos SVG sin titulo/aria cuando comunican accion.
- Mantener foco en modales y overlays.
- Agregar `aria-live` en toasts o errores globales importantes.

## Seguridad frontend

Prioridades:

1. Reducir exposicion de tokens en `localStorage` o compensar con CSP fuerte.
2. No mostrar Devtools de React Query en produccion.
3. Evitar logs de version/PWA en produccion.
4. Revisar endpoints de redireccion externa como checkout para validar que backend entregue URLs confiables.
5. No confiar en permisos frontend como control real: deben seguir siendo solo UX; Django debe bloquear.

## Performance

Lo positivo:

- Hay lazy loading por paginas.
- Build genera chunks separados.
- El mayor vendor observado es `react-dom` y `framer-motion`; no hay un bundle unico gigante.

Mejoras:

- Revisar si `framer-motion` se justifica globalmente o se puede importar solo donde aporta.
- Evitar importar componentes demo/ejemplo en rutas reales.
- Medir tablas grandes con paginacion real.
- Memoizar columnas/handlers donde haya tablas densas, pero solo despues de medir.

## Testing recomendado

Prioridad inmediata:

- Arreglar la corrida completa de Vitest.
- Agregar test de smoke para `App` autenticado con rutas principales mockeadas.
- Tests para dashboard admin general:
  - `scope=analytics`
  - `scope=global`
  - `scope=school` sin colegio
  - `scope=school&colegio_id=...`
- Tests de `apiClient` con refresh concurrente y errores no JSON.
- Tests de permisos/rutas para cada rol principal.

Tambien conviene agregar Playwright para flujos reales:

- Login.
- Dashboard admin general.
- Selector de colegio.
- Asistencias profesor/admin.
- Pago o transferencia en modo mock.

## Roadmap sugerido

### Semana 1: estabilidad

- Unificar `QueryClientProvider`.
- Corregir encoding visible.
- Desactivar Devtools en produccion.
- Reparar `npm run test:run`.
- Reemplazar `alert()` en suscripciones.

### Semana 2: dashboard y tenant

- Extraer hooks/componentes del dashboard.
- Formalizar seleccion de colegio para admin general.
- Separar tenant visual de scope de datos.
- Agregar tests de dashboard por scope.

### Semana 3: paginas administrativas

- Refactor de `AdminAttendancePage`.
- Refactor de `AdminStudentsPage`.
- Unificar paginacion, filtros, errores y toasts.

### Semana 4: calidad transversal

- Agregar lint/format.
- Mover docs/ejemplos fuera de `src`.
- Crear contrato de rutas en archivo dedicado.
- Agregar smoke e2e con Playwright.

## Checklist corto

- [ ] Un solo `QueryClientProvider`.
- [ ] Devtools solo en desarrollo.
- [ ] Encoding UTF-8 corregido.
- [ ] `npm run test:run` termina sin timeout.
- [ ] Tokens revisados para produccion.
- [ ] Hooks de datos unificados sobre React Query.
- [ ] Rutas fuera de `App.jsx`.
- [ ] Dashboard separado en hooks/componentes.
- [ ] `alert()` eliminado.
- [ ] Docs y ejemplos fuera de `src`.
