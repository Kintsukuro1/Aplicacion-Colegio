# E2E Testing con Playwright

## Descripción

Este directorio contiene tests **End-to-End (E2E)** usando [Playwright](https://playwright.dev) para validar flujos críticos de la aplicación:

- **Login Flow**: Validación de autenticación y credenciales inválidas
- **Dashboard Admin**: Carga correcta del dashboard y navegación
- **School/Tenant Selector**: Cambio de colegio y mantenimiento de sesión
- **Admin Attendance**: Flujo de registro de asistencias

## Configuración

El archivo `playwright.config.js` en la raíz del proyecto define:
- Base URL: `http://localhost:5173` (desarrollo)
- Browsers: Chromium, Firefox, WebKit
- Server de desarrollo: Auto-inicia con `npm run dev`
- Reportes en HTML
- Screenshots y traces en fallos

## Ejecución

### Ejecutar todos los tests
```bash
npm run e2e
```

### Ejecutar tests en modo UI interactivo
```bash
npm run e2e:ui
```

### Ejecutar tests en modo debug
```bash
npm run e2e:debug
```

### Ver reporte HTML del último run
```bash
npm run e2e:report
```

### Ejecutar un archivo específico
```bash
npx playwright test tests/e2e/login.spec.js
```

### Ejecutar un test específico
```bash
npx playwright test -g "should render login page"
```

## Estructura

```
tests/
├── e2e/
│   ├── fixtures/
│   │   └── auth.js         # Fixtures para autenticación
│   ├── login.spec.js       # Tests de login
│   ├── dashboard.spec.js   # Tests de dashboard
│   ├── attendance.spec.js  # Tests de registro de asistencias
│   └── school-selector.spec.js  # Tests de selector de colegio
└── ... (otros tests)
```

## Fixtures de Autenticación

El archivo `fixtures/auth.js` proporciona fixtures pre-configurados:

- `authenticatedPage`: Página con acceso a la app
- `adminPage`: Página con login realizado como admin

Uso:
```javascript
import { test, expect } from '../fixtures/auth.js';

test('should do something as admin', async ({ adminPage }) => {
  await adminPage.goto('/some-page');
  // ...
});
```

## Consideraciones de Prueba

### Base de datos de test
Los tests asumen:
- Servidor de desarrollo corriendo en `http://localhost:5173`
- Backend disponible en las URLs configuradas en la app
- Credenciales de test válidas (ajustar según tu setup)

### Usuarios de test
Actualmente los tests usan:
- Email: `admin@test.cl`
- Password: `password123`

**Ajusta estas credenciales** según tu entorno de test antes de ejecutar.

### Timeouts
- Navegación: 10 segundos
- Búsqueda de elementos: 5 segundos
- Esperas genéricas: configurable por test

## Mejoras Futuras

- [ ] Fixtures parametrizados para múltiples usuarios (profesor, apoderado, etc.)
- [ ] Tests de flujo de asistencia completo (crear, actualizar, guardar)
- [ ] Tests de validación de datos y errores
- [ ] Tests de PWA y offline mode
- [ ] Integración con CI/CD (GitHub Actions, etc.)
- [ ] Tests de performance y carga
- [ ] Screenshots en cada paso del flujo

## Debugging

### Ver eventos y trazas
```bash
npm run e2e:debug
```

### Ejecutar un test específico paso a paso
```bash
npx playwright test tests/e2e/login.spec.js --debug
```

### Inspeccionar selector
```bash
npx playwright codegen http://localhost:5173
```

Este comando abre una herramienta interactiva para generar selectores y grabar tests.

## Referencias

- [Documentación Playwright](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [API Reference](https://playwright.dev/docs/api/class-page)
