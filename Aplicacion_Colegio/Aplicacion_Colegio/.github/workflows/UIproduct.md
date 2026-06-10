---
agent: agent
description: Orquesta Vision, Muse, Palette, Flow y Artisan para diseñar y construir interfaces de producto completas con calidad de diseño, UX y frontend.
---

# Workflow: UI/UX Nivel Producto

Cuando uses este workflow, sigue este orden exacto usando cada skill referenciado.

## Skills disponibles

- [Vision](./../skills/vision/SKILL.md) — define dirección visual y concepto
- [Muse](./../skills/muse/SKILL.md) — crea sistema de diseño (tokens, estilos)
- [Palette](./../skills/palette/SKILL.md) — optimiza UX, accesibilidad y usabilidad
- [Flow](./../skills/flow/SKILL.md) — diseña animaciones e interacción
- [Artisan](./../skills/artisan/SKILL.md) — implementa en frontend

---

## Cómo ejecutar este workflow

### PASO 1 — Vision define el concepto

Usando las reglas de [Vision](./../skills/vision/SKILL.md):

- Entiende el objetivo del producto o feature
- Propón 3 direcciones visuales (segura / balanceada / bold)
- Establece principios visuales: colores, jerarquía, tono

👉 Output esperado:
- Dirección visual elegida con justificación
- Decisiones clave de layout, componentes y patrones

---

### PASO 2 — Muse construye el sistema de diseño

Usando las reglas de [Muse](./../skills/muse/SKILL.md):

- Define design tokens (color, spacing, typography, radius)
- Reemplaza cualquier valor hardcodeado por tokens
- Establece componentes base reutilizables

👉 Output esperado:
- Tokens definidos con nombres semánticos
- Sistema de diseño simple y escalable

---

### PASO 3 — Palette optimiza UX y accesibilidad

Usando las reglas de [Palette](./../skills/palette/SKILL.md):

- Reduce carga cognitiva
- Asegura todos los estados: loading, error, success, empty
- Aplica WCAG 2.2 AA (contraste, foco, etiquetas, teclado)
- Mejora formularios, feedback y jerarquía de CTAs

👉 Output esperado:
- Flujos UX mejorados
- Estados completos implementados
- Accesibilidad aplicada en código

---

### PASO 4 — Flow diseña la interacción

Usando las reglas de [Flow](./../skills/flow/SKILL.md):

- Identifica puntos de interacción (hover, click, transiciones)
- Define animaciones útiles: 150–300ms, ease-out, GPU-friendly
- Añade fallback para `prefers-reduced-motion`

👉 Output esperado:
- Microinteracciones definidas con propósito
- Código CSS/JS limpio y performante

---

### PASO 5 — Artisan implementa en frontend

Usando las reglas de [Artisan](./../skills/artisan/SKILL.md):

- Implementa los componentes con TypeScript
- Respeta los tokens de Muse y las reglas UX de Palette
- Maneja todos los estados (loading, error, empty)
- Asegura accesibilidad semántica (ARIA, teclado)

👉 Output esperado:
- Código limpio, tipado y listo para producción
- Componentes reutilizables y bien estructurados

---

## Reglas del workflow

- ✅ Seguir el orden exacto — no saltar pasos
- ✅ UX antes que UI (Palette antes que Artisan)
- ✅ Sistema antes que implementación (Muse antes que Artisan)
- ✅ Validar cada paso antes de continuar
- ❌ No implementar sin dirección visual definida (Vision)
- ❌ No animar sin propósito claro (Flow)
- ❌ No hardcodear valores — siempre usar tokens (Muse)

---

## Cuándo usar cada skill directamente

| Situación | Skill |
|---|---|
| Necesitas definir estilo visual | Vision |
| Falta consistencia de UI o tienes valores hardcodeados | Muse |
| Problemas de UX, accesibilidad o estados incompletos | Palette |
| Interacciones pobres o inexistentes | Flow |
| Necesitas código frontend listo para producción | Artisan |
| Todo el flujo completo | Este workflow |

---

## Cómo invocarlo

En el chat de Copilot escribe:

> "Usando #ui-product.prompt.md diseña este dashboard"

> "Con #ui-product.prompt.md mejora el UX de este formulario"

> "Usando #ui-product.prompt.md crea una landing page completa"