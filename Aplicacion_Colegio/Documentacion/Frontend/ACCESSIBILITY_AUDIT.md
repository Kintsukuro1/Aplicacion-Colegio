# Auditoría de Accesibilidad (WCAG 2.2) - Colegio SaaS Frontend

Fecha: 2026-05-10  
Norma: WCAG 2.2 Level AA (recomendado para SaaS educativo)

## Hallazgos Iniciales

### ✅ Cumplimientos Actuales

1. **Semántica HTML**: Las páginas usan elementos semánticos (`<nav>`, `<main>`, `<header>`, `<table>` con `<th>`, etc.)
2. **Contraste de Color**: La paleta teal/blanco mantiene contraste >4.5:1 en textos principales
3. **Responsive Design**: Mobile-first approach con breakpoints adecuados
4. **Navegación por Teclado**: Buttons y links son focusables con outline visible

### ⚠️ Áreas de Mejora

#### 1. **Labels y ARIA**
- [ ] Verificar que TODOS los inputs tengan `<label>` o `aria-label`
- [ ] Revisar modales: agregar `aria-modal="true"` y `role="dialog"`
- [ ] Tablas: agregar `aria-label` a tablas sin caption visible
- [ ] Botones de iconos: necesitan text o `aria-label`

**Ejemplo de mejora:**
```html
<!-- ❌ Malo -->
<button onClick={toggleMenu}>☰</button>

<!-- ✅ Bueno -->
<button onClick={toggleMenu} aria-label="Abrir menú">☰</button>
```

#### 2. **Focus Management**
- [ ] Focus trap en Modales (FocusTrap component)
- [ ] Focus restaurado al cerrar Modal
- [ ] Skip-to-main link para saltar navegación

**Ejemplo:**
```jsx
// En Modal component:
useEffect(() => {
  const previousActiveElement = document.activeElement;
  
  return () => {
    previousActiveElement?.focus?.(); // Restore focus on close
  };
}, []);
```

#### 3. **Imágenes y SVGs**
- [ ] Todos los SVGs deben tener `role="img"` y `aria-label` si son semánticos
- [ ] Imágenes decorativas: `aria-hidden="true"`
- [ ] Alt text en `<img>` (aunque son pocas en esta app)

**Ejemplo:**
```jsx
// ❌ Malo
<svg>...</svg>

// ✅ Bueno
<svg role="img" aria-label="Icono de error">...</svg>

// Para decorativas:
<svg aria-hidden="true" focusable="false">...</svg>
```

#### 4. **Anuncios de Cambio (aria-live)**
- [x] Toasts/Notificaciones: Ya tienen `aria-live="polite"` (revisar Toast component)
- [ ] Validación de errores: Agregar `aria-invalid="true"` y `aria-describedby` a inputs con error

#### 5. **Paginación**
- [ ] Agregar `aria-label="Página actual: X de Y"` a indicador de página
- [ ] Botones prev/next: aria-label descriptivo

#### 6. **Tablas Grandes (AdminStudentsPage, etc.)**
- [ ] Encabezados `<th scope="col">` o `<th scope="row">`
- [ ] Caption: `<caption>` o `aria-label` visible
- [ ] Datos complejos: considerar `aria-describedby`

### 📊 Prioridad de Fixes

| Prioridad | Item | Impacto | Esfuerzo |
|-----------|------|--------|----------|
| 🔴 Critical | Focus trap en Modales | Alto | Bajo |
| 🔴 Critical | Labels en todos los inputs | Alto | Medio |
| 🟠 High | aria-label en botones icono | Alto | Bajo |
| 🟠 High | aria-describedby en validación | Medio | Bajo |
| 🟡 Medium | Skip-to-main link | Bajo | Muy Bajo |
| 🟡 Medium | aria-label en SVGs | Bajo | Bajo |

## Herramientas de Validación Recomendadas

1. **axe DevTools** (Chrome/Firefox extension)
   - Scan automático de a11y issues
   - Integración con CI/CD posible

2. **WAVE (WebAIM)** 
   - Color contrast checker
   - Form label validation

3. **Manual Testing**
   - Navegar solo con Tab/Shift+Tab
   - Navegador con pantalla aumentada (120-200%)
   - Lector de pantalla: NVDA (Windows), VoiceOver (Mac)

## Plan de Implementación

### Fase 1: Critical Fixes (1-2 horas)
1. Agregar FocusTrap component a Modales
2. Auditar y fijar labels en LoginPage, RegisterPage, formularios

### Fase 2: High Priority (2-3 horas)
1. Agregar aria-label a botones de icono globales
2. Mejorar validación con aria-invalid + aria-describedby
3. Mejorar componente Toast con aria-live

### Fase 3: Polish (1 hora)
1. Add skip-to-main link
2. Agregar aria-label a SVGs y iconos
3. Revisar Tablas con axe DevTools

## Referencias

- [WCAG 2.2 Guidelines](https://www.w3.org/WAI/WCAG22/quickref/)
- [React Accessibility Patterns](https://www.a11y-101.com/design/form-labels)
- [axe-core Rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)
