---
agent: agent
description: Orquesta Nexus, Sherpa, Darwin y Sigil para resolver tareas complejas de forma estructurada.
---

# Workflow: Orquestación Core

Cuando uses este workflow, sigue este orden exacto usando cada skill referenciado.

## Skills disponibles

- [Nexus](./../skills/nexus/SKILL.md) — coordina y decide el plan
- [Sherpa](./../skills/sherpa/SKILL.md) — divide la tarea en pasos ejecutables
- [Darwin](./../skills/darwin/SKILL.md) — evalúa salud del sistema y simplifica
- [Sigil](./../skills/sigil/SKILL.md) — genera skills reutilizables si detecta patrones repetidos

---

## Cómo ejecutar este workflow

### PASO 1 — Nexus analiza la tarea
Usando las reglas de Nexus:
- Entiende el objetivo completo
- Decide si la tarea es simple (1 skill) o compleja (varios skills)
- Define el plan antes de ejecutar cualquier cosa

### PASO 2 — Sherpa divide el trabajo
Si la tarea es compleja o tiene más de un paso:
- Divide en pasos de 5–15 minutos cada uno
- Muestra solo el paso actual
- Detecta riesgos o bloqueos antes de continuar

### PASO 3 — Ejecuta paso a paso
- Un paso a la vez
- Valida cada paso antes de avanzar
- Si algo falla → vuelve a Sherpa para ajustar

### PASO 4 — Darwin evalúa el resultado
Al terminar la ejecución:
- ¿El sistema quedó más simple o más complejo?
- ¿Hay algo redundante o innecesario que se introdujo?
- ¿El cambio fue justificado?

### PASO 5 — Sigil captura patrones (opcional)
Si durante la ejecución detectaste un patrón que se va a repetir:
- Genera un skill reutilizable con Sigil
- Que siga las convenciones del proyecto

---

## Cuándo usar cada skill directamente

| Situación | Skill |
|---|---|
| Tarea compleja con múltiples archivos | Nexus + Sherpa |
| Te sientes bloqueado o sin dirección | Sherpa |
| El sistema creció demasiado | Darwin |
| Repites el mismo patrón varias veces | Sigil |
| Todo lo anterior junto | Este workflow completo |

---

## Reglas que siempre aplican

- Nunca hacer todo de una vez
- Validar antes de avanzar
- Preferir lo simple sobre lo complejo
- No agregar pasos si no son necesarios

---

## Cómo invocarlo

En el chat de Copilot escribe algo como:

> "Usando #orchestration.prompt.md revísame este módulo y dime cómo mejorarlo"

> "Con #orchestration.prompt.md quiero agregar autenticación a mi app"

> "Usando #orchestration.prompt.md analiza si mi estructura de carpetas tiene sentido"
