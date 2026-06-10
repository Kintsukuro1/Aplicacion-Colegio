# API Contract Dashboard v1

## Endpoint
- `GET /api/v1/dashboard/resumen/`

## Query Params
- `scope`: `auto|self|school|analytics|global`
- `colegio_id`: opcional para admin global; obligatorio para `school`/`analytics` si el usuario no tiene colegio por defecto.

## Auth
- Requiere JWT o session autenticada.
- Requiere al menos una capability dashboard:
  - `DASHBOARD_VIEW_SELF`
  - `DASHBOARD_VIEW_SCHOOL`
  - `DASHBOARD_VIEW_ANALYTICS`
- `global` solo para `SYSTEM_ADMIN`.

## Stable Contract
- `contract_version` viene desde constante compartida backend:
  - `backend/apps/api/contracts.py` -> `DASHBOARD_CONTRACT_VERSION`

Respuesta base:

```json
{
  "contract_version": "1.0.0",
  "scope": "school",
  "generated_at": "2026-03-05",
  "context": {
    "user_id": 10,
    "role": "Administrador escolar",
    "colegio_id": 123,
    "is_global_admin": false
  },
  "available_scopes": ["school"],
  "sections": {
    "self": null,
    "school": {},
    "analytics": null
  }
}
```

## Sections by Scope
- `self`: metricas personales del usuario autenticado.
- `school`: metricas operativas del colegio.
- `analytics`: metricas agregadas para analitica.
- `global`: para admin global, rellena `school` + `analytics` sin filtro de colegio.

## Backward Compatibility
- El contrato nuevo reemplaza la respuesta legacy `{"scope": "...", "metrics": {...}}`.
- Frontend React debe consumir `sections` y no `metrics` plano.

## React Mapping Suggested
- `scope=self` -> `sections.self`
- `scope=school` -> `sections.school`
- `scope=analytics` -> `sections.analytics`
- `scope=auto` -> usar `scope` devuelto por API para render condicional.

## Error Cases
- `403`: capability/scope no permitido.
- `400`: parametros invalidos (`scope`, `colegio_id`).
