# Indice Maestro de Documentacion

Este directorio es la fuente canonica de documentacion tecnica del proyecto.

## Convenciones de nombres
- Contratos API: `API_CONTRACT_<DOMINIO>_V<NUMERO>.md`
- Planes: `PLAN_<TEMA>.md`
- Seguimientos: `SEGUIMIENTO_<TEMA>_<YYYY-MM-DD>.md` cuando aplique fecha
- Runbooks: `RUNBOOK_<TEMA>.md`
- Auditorias: `<TEMA>_AUDIT_<DETALLE>.md` o nombres historicos existentes

Nota: en esta fase no se renombran archivos historicos para no romper referencias existentes.

## Contratos
- [ACADEMIC_SERVICE_CONTRATO.md](ACADEMIC_SERVICE_CONTRATO.md)
- [API_CONTRACT_DASHBOARD_V1.md](API_CONTRACT_DASHBOARD_V1.md)
- [API_CONTRACT_MOBILE_MVP_V1.md](API_CONTRACT_MOBILE_MVP_V1.md)

## Planes
- [PLAN_CHILE_MEJORAS.md](PLAN_CHILE_MEJORAS.md)
- [PLAN_NUEVOS_ROLES_CAPABILITIES.md](PLAN_NUEVOS_ROLES_CAPABILITIES.md)

## Seguimientos
- [SEGUIMIENTO_API_PRODUCCION.md](SEGUIMIENTO_API_PRODUCCION.md)
- [SEGUIMIENTO_FIX_VISTAS_ESTUDIANTE_2026-03-12.md](SEGUIMIENTO_FIX_VISTAS_ESTUDIANTE_2026-03-12.md)
- [SEGUIMIENTO_LIBRO_CLASES_DECRETO67_2026-03-15.md](SEGUIMIENTO_LIBRO_CLASES_DECRETO67_2026-03-15.md)
- [SEGUIMIENTO_LIMPIEZA_DOCUMENTAL_2026-03-16.md](SEGUIMIENTO_LIMPIEZA_DOCUMENTAL_2026-03-16.md)
- [SEGUIMIENTO_MODELS_NUEVOS_ROLES_A_MODELS.md](SEGUIMIENTO_MODELS_NUEVOS_ROLES_A_MODELS.md)
- [SEGUIMIENTO_NOTIFICACIONES_PRODUCCION.md](SEGUIMIENTO_NOTIFICACIONES_PRODUCCION.md)
- [SEGUIMIENTO_ROADMAP_PRODUCTO_2026-03-16.md](SEGUIMIENTO_ROADMAP_PRODUCTO_2026-03-16.md)

## Frontend
- [FRONTEND_REACT_BOOTSTRAP.md](FRONTEND_REACT_BOOTSTRAP.md)
- [FRONTEND_REACT_TODO.md](FRONTEND_REACT_TODO.md)
- [views_example_template_mapping.py](views_example_template_mapping.py)

## Operacion y ejecucion
- [EJECUCION_PASOS_11_12_13.md](EJECUCION_PASOS_11_12_13.md)
- [RUNBOOK_GATEWAY_BACKUP.md](RUNBOOK_GATEWAY_BACKUP.md)

## Auditorias
- [ORM_ACCESS_AUDIT.md](ORM_ACCESS_AUDIT.md)
- [tenant_manager_audit_stage_1_1.md](tenant_manager_audit_stage_1_1.md)

## Regla de uso
- Crear nuevos documentos en este directorio.
- Evitar volver a generar archivos de documentacion activa en la raiz OUTER/docs.
- Si un documento queda obsoleto, dejar referencia al reemplazo en la primera seccion del archivo.
