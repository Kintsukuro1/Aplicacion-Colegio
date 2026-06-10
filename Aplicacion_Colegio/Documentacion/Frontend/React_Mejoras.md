# Revision React - Mejoras y deuda tecnica

Fecha: 2026-05-11
Alcance revisado: `Aplicacion_Colegio/frontend-react`

## Resumen ejecutivo

La aplicacion React ha madurado significativamente tras las Fases 3 y 4 de refactorización. Cuenta con una arquitectura robusta basada en Vite, React Router, TanStack Query (`useQuery`), Zustand, code splitting por paginas, pruebas estabilizadas con Vitest y una clara separación de responsabilidades a través de hooks de datos, modales y componentes compartidos de UI.

Se han resuelto problemas críticos previos, como la duplicidad de `QueryClientProvider`, la inestabilidad de la suite de pruebas automatizadas, el overcoding en el Dashboard y la coexistencia problemática de hooks propios (`useFetch`) y React Query.

Sin embargo, aún persiste deuda técnica relacionada con la seguridad del lado del cliente, configuraciones globales (encoding) y mejoras de usabilidad en dispositivos móviles o PWA.

**Prioridades recomendadas actuales:**

1. Fortalecer el manejo de sesión (actualmente en `localStorage`) para mayor seguridad.
2. Implementar los Critical A11y fixes (focus trap, labels, aria-live).
3. Validar el flujo PWA de actualización en producción (banner + recarga controlada).
4. Continuar optimizando accesibilidad y performance en tablas masivas.

---

## Mejoras Realizadas (Resueltas)

- **[RESUELTO] Doble `QueryClientProvider`:** Se unificó el cliente global, previniendo comportamientos anómalos de caché. Devtools solo está disponible en entorno de desarrollo.
- **[RESUELTO] Estabilización de Vitest:** Se arreglaron las fugas de temporizadores y el desmontaje incorrecto en los tests, logrando una suite confiable.
- **[RESUELTO] Deuda de Estructura por Hooks (`useFetch`):** Se completó la Fase 4 de migración, estandarizando toda la obtención de datos mediante TanStack Query y removiendo `useFetch`.
- **[RESUELTO] Overcoding en Dashboard:** El Dashboard fue descompuesto y modernizado, integrando analíticas por `scope` (`analytics`, `global`, `school`) y separando la lógica en hooks dedicados.
- **[RESUELTO] Consistencia de UI/Errores:** Se generalizó el uso de Skeletons y Toasts para notificaciones globales, reemplazando `alert()` y spinners redundantes.
- **[RESUELTO] Fuga de renders en `AdminAttendancePage`:** Se estabilizó el valor vacío devuelto por `usePagination` para que no genere un array nuevo en cada render antes de recibir datos. Se hizo esto porque el efecto de la página reescribía estado a partir de `attendanceRows`, y ese array inestable podía mantener la suite de Vitest viva aunque las aserciones ya hubieran pasado. El objetivo fue cerrar el ciclo de render y conseguir que la prueba salga limpiamente sin afectar el comportamiento funcional.
- **[RESUELTO] Framework E2E para tests de flujos críticos:** Se implementó **Playwright** como framework de testing end-to-end. Se creó `playwright.config.js` con configuración completa (Chromium, Firefox, WebKit, base URL, reportes HTML). Se implementaron 4 suites de tests críticos: Login, Dashboard Admin, School/Tenant Selector y Admin Attendance. Se agregaron scripts npm: `npm run e2e`, `npm run e2e:ui`, `npm run e2e:debug`. Se documentó todo en `tests/e2e/README.md`. El objetivo es validar flujos de usuario completos desde el navegador, proporcionando confianza en la integración entre frontend y backend, y detectando regresos en UI/UX que los tests unitarios no capturan. Los tests son agnósticos a la implementación (usan selectores robustos basados en roles y contenido) y cubren las principales journeys del usuario según el plan original.- **[RESUELTO] Refuerzo de Seguridad JWT (localStorage):** Se mejoró el manejo de tokens en `authStore.js` añadiendo:
  - **Validación de expiración**: Nueva función `isTokenExpired()` que decodifica el JWT y valida el claim `exp`, considerando tokens expirados si tienen <1 minuto restante. Esto mejora la UX al detectar tokens vencidos antes de hacer requests fallidos.
  - **Información del token**: Nueva función `getTokenInfo()` que retorna `subject`, `expiresAt`, `isExpired`, `expiresIn` para debugging y monitoreo.
  - **Sincronización multi-tab**: Nueva función `initMultiTabSync()` que escucha el evento `storage` global. Si el token es removido en otra tab (logout), la tab actual recibe un evento `auth-logout` personalizado. Se inicializa en `main.jsx` y se escucha en `App.jsx`. Esto previene que una tab mantenga sesión activa después de logout en otra tab.
  - **Actualización de `isAuthenticated()`**: Ahora valida tanto que haya token como que no esté expirado.
  El objetivo es mejorar la robustez de la sesión en localStorage (sin exponer a XSS adicional) mientras se evalúa migración futura a HttpOnly cookies. Se documentó el análisis en `docs/SECURITY_JWT_ANALYSIS.md`. Los tests siguen pasando (AdminAttendancePage: 5 tests en 3.35s).
- **[RESUELTO] Optimización PWA, SEO y Accesibilidad (Fase 6):** Se realizaron múltiples mejoras:
  - **UpdateListener.jsx**: Mejorado con mejor UX - ahora expone función global `window.__updateApp()` para reload manual, y registra versión + timestamp para debugging.
  - **Update flow visible**: Se incorporó banner visible con botón de recarga y manejo de `SKIP_WAITING`/`controllerchange` para aplicar versiones nuevas de forma confiable.
  - **Service Worker (sw.js)**: Agregado logging condicional en desarrollo (detecta localhost) sin afectar producción. Logs detallados de estrategias network-first y stale-while-revalidate. Mejor diagnóstico de offline behavior.
  - **Version hash**: `BUILD_VERSION` ahora usa timestamp completo para detectar múltiples deploys en un mismo día.
  - **usePageMeta hook**: Nuevo hook para actualizar dinámicamente título, meta description, Open Graph tags (og:title, og:description, og:image, og:type). También función imperativa `setPageMeta()` para contextos no-React.
  - **index.html mejorado**: Agregados og:* tags, Twitter Card, keywords, structured data (JSON-LD) de SoftwareApplication, canonical URL placeholder, apple-mobile-web-app-title, meta robots.
  - **Auditoría de Accesibilidad (A11y)**: Creado documento `docs/ACCESSIBILITY_AUDIT.md` con hallazgos WCAG 2.2, plan de implementación (Critical/High/Medium priority), checklist de herramientas (axe DevTools, WAVE), y guías de best practices (focus trap, aria-labels, aria-describedby, alt text). Objetivo es preparar el terreno para cumplimiento WCAG AA.
  El propósito de Fase 6 es mejorar experiencia offline-first, SEO para usuarios públicos, e inclusividad para usuarios con discapacidades. Los cambios son backward-compatible y no requieren deps externas.
- **[EN PROGRESO] Refactorización de Páginas Grandes (Fase 7):** Se crearon 4 custom hooks reutilizables para eliminar duplicación entre AdminStudentsPage y CalendarEventsPage:
  - **useFormCRUD**: Hook centralizado para estado de formulario + CRUD (create, read, update, delete). Gestiona `form`, `editingId`, `loading`, `saving`, `error`. Métodos: `create()`, `update()`, `delete()` con manejo automático de toasts y callbacks `onSuccess`. Reduce ~50 líneas de boilerplate por página.
  - **usePermissionChecks**: Hook para validación de permisos reutilizable. Toma arrays de capabilities por operación (view, create, update, delete) y retorna `canView`, `canCreate`, `canUpdate`, `canDelete` con memoization. Usa la infraestructura de capabilities existente (`hasAnyCapability`).
  - **useBulkDeactivate**: Hook para operaciones masivas con fallback automático. Si endpoint bulk falla con 404/405, automáticamente intenta eliminar registros uno por uno. Tracking de éxito/fallos con opción de reintentar. Útil para AdminStudentsPage.
  - **useEventFilters**: Hook para gestión de filtros con query building. Estado: `filters`, `updateFilter()`, `clearFilters()`, `activeFilters` (memoizado), `buildQuery()`. Simplifica lógica de filtros en CalendarEventsPage.
  - **AdminStudentsPage refactorizado**: Reducido de ~560 líneas a ~300 líneas usando los nuevos hooks. Eliminadas funciones de CRUD manual, permiso checking complejo, y bulk deactivate logic. Código ahora es más legible y mantenible.
  - **CalendarEventsPage refactorizado**: Migrado a `useFormCRUD`, `useEventFilters`, `usePermissionChecks` y `usePagination`. Se eliminó la lógica manual de fetch y permisos legacy.
  Propósito: Reducir cognitive load, facilitar testing, reutilizar lógica entre páginas.

- **[RESUELTO] Correcciones críticas de CRUD y paginación:**
  - Se corrigió `useFormCRUD` para usar los toasts reales y soportar mapeo de IDs/payloads.
  - Se corrigió `useBulkDeactivate` para usar el cliente API correcto y notificaciones reales.
  - Se ajustó `usePagination` a paginación 1-based y se arregló el query de búsqueda en AdminStudents.

- **[RESUELTO] Tenant visual vs scope global:** Se agregó override visual del tenant sincronizado con el selector de colegio del dashboard para administradores globales, separando branding de scope de datos.

- **[RESUELTO] Normalización de encoding en frontend-react:** Se limpiaron separadores y placeholders en UI y estilos para evitar caracteres corruptos.
- **[RESUELTO] A11y incremental:** Se agregaron labels accesibles en la barra de búsqueda, roles/aria-live apropiados en toasts y anuncios ARIA para errores/cargas.
---

## Hallazgos Críticos Pendientes

### 1. Sesión basada en `localStorage`

Archivo: `src/lib/authStore.js`

Los access/refresh tokens se guardan en `localStorage`.

**Impacto:**
- Mayor exposicion ante XSS.
- Logout remoto y refresh pueden quedar en estados ambiguos si una pestana falla.

**Recomendación:**
- Para produccion, evaluar cookies `HttpOnly`, `Secure`, `SameSite` enviadas y gestionadas desde Django.
- Si se mantiene `localStorage`, reforzar políticas de CSP, expiración local y limpieza multi-tab sincronizada mediante el evento `storage`.

### 2. Textos residuales con encoding roto

Se normalizó el encoding en frontend-react y estilos. Pendiente: validar en backend y documentos fuera del alcance frontend si aparecen caracteres corruptos.

---

## Áreas de Oportunidad a Futuro

### PWA / Service Worker

Archivos: `src/main.jsx`, `src/components/UpdateListener.jsx`, `public/sw.js`

**Mejoras:**
- Restringir logs a desarrollo.
- Verificar el comportamiento del banner de actualización en producción.
- Verificar el cleanup de listeners en los eventos del Service Worker.

### Mobile y Accesibilidad

**Mejoras:**
- Comprobar que la navegación inferior móvil (`MobileBottomNav`) no superponga botones de acción primarios o elementos de paginación en tablas.
- Revisar `aria-live` en el nuevo sistema de Toasts.
- Mantener estrictamente el foco (Focus Trap) dentro de los nuevos Modales implementados en la Fase 3.

### Seguridad Frontend

**Prioridades:**
- No confiar exclusivamente en el frontend para ocultar vistas; garantizar que los endpoints de Django estén rigurosamente protegidos por rol.
- Revisar flujos externos (ej. redirecciones a pasarelas de pago) para confirmar que las URLs provienen del backend y están validadas.

---

## Roadmap Sugerido (Próximas Fases)

### Fase 5: Consolidación de Seguridad y E2E ✓ COMPLETADA
- ✓ Implementación de Playwright para flujos críticos End-to-End (E2E): Login, Dashboard Admin, Selector de Colegio, Registro de Asistencia.
- ✓ Refuerzo de validación de expiración JWT y sincronización multi-tab en localStorage.
- 🔄 Próximo: Migración a HttpOnly cookies (requiere coordinar con backend Django).

### Fase 6: Optimización PWA, SEO y Accesibilidad ✓ COMPLETADA
- ✓ Service Worker mejorado con logging condicional en desarrollo.
- ✓ UpdateListener con mejor UX y función de reload manual.
- ✓ Hook usePageMeta para metatags dinámicos y Open Graph.
- ✓ Auditoría WCAG 2.2 Level AA con plan de implementación.
- 🔄 Próximo: Implementar Critical A11y fixes (focus trap, aria-labels, validación).

### Fase 7: Refactorización de Páginas Grandes (En Progreso)
- ✓ Creación de 4 custom hooks reutilizables: useFormCRUD, usePermissionChecks, useBulkDeactivate, useEventFilters
- ✓ Refactorización de AdminStudentsPage (560L → 300L)
- ✓ Refactorización de CalendarEventsPage (439L → ~220L estimado)
- 🔄 Próximo: Extraer componentes JSX reutilizables (FormGrid, SummaryCards, etc.)

### Fase 8: Unificación de Errores y Validación Global
- Definir único patrón para errores recuperables vs fatales.
- Global error boundary con retry lógica.
- Standardizar todas las notificaciones Toast/Validation.
- Error telemetry/logging para diagnóstico en producción.

### Fase 9: Testing Comprehensive (Coverage & Stability)
- Aumentar test coverage en páginas críticas a >80%.
- Implementar tests de accessibilidad con jest-axe.
- Mejorar tests E2E con escenarios de error y edge cases.
- Performance testing con Lighthouse CI.

### Fase 10: Producción & Monitoreo
- Implementar error tracking (Sentry o similar).
- Analytics y session replay (LogRocket o similar).
- Performance monitoring con Web Vitals.
- Security audit completo (penetration testing).

## Checklist Actual

- [x] Un solo `QueryClientProvider` y hooks centralizados.
- [x] Migración completa a TanStack Query (Fase 4).
- [x] Tests de componentes sin fugas de memoria o temporizadores colgados.
- [x] Modernización de componentes y UI (Modales, Skeletons, Toasts).
- [x] Dashboard analítico funcional y modular.
- [x] Tests E2E con Playwright para flujos críticos (Fase 5).
- [x] Refuerzo de seguridad JWT: validación de expiración y sync multi-tab.
- [x] Optimización PWA: mejor Service Worker logging y UpdateListener UX.
- [x] SEO dinámico: hook usePageMeta, Open Graph, metadatos mejorados.
- [x] Auditoría de Accesibilidad: WCAG 2.2 checklist y plan de implementación.
- [x] Refactorización Fase 7: Custom hooks reutilizables y AdminStudentsPage.
- [x] Refactorización CalendarEventsPage (continuación Fase 7).
- [ ] Implementación de Critical A11y fixes (focus trap, labels, validación completa).
- [ ] Migración a HttpOnly cookies (requiere cambios backend Django).
- [x] Estabilización del contexto de Tenant vs Scope Global.
- [x] Encoding garantizado en frontend-react.
