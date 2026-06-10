# GUIA DE PRODUCCION PARA LLM — SISTEMA COLEGIO SaaS

## PROPÓSITO

Este documento define las reglas obligatorias que cualquier LLM debe seguir al trabajar sobre este proyecto.

Su objetivo es garantizar:

* estabilidad
* seguridad
* consistencia arquitectónica
* escalabilidad comercial

---

# PRINCIPIO FUNDAMENTAL

El LLM NO tiene autoridad para rediseñar el sistema.

El LLM solo puede:

* mejorar
* corregir
* extender

sin romper contratos existentes.

---

# REGLA 1 — FUENTE UNICA DE AUTORIZACION

Toda autorización debe pasar por:

PolicyService

Está prohibido:

* usar user.role.code directamente
* usar strings de rol
* implementar lógica de autorización fuera de PolicyService

Incorrecto:

```
if user.role.code == "ADMIN":
```

Correcto:

```
PolicyService.require_capability(user, "USER_CREATE")
```

---

# REGLA 2 — NO ACCESO DIRECTO AL ORM DESDE VIEWS

Las views NO pueden contener:

```
Model.objects.get
Model.objects.filter
Model.objects.create
```

Las views solo pueden llamar services.

---

# REGLA 3 — NO LOGICA DE NEGOCIO FUERA DE SERVICES

Toda lógica debe vivir en:

```
backend/apps/*/services/
```

Nunca en:

* views
* models
* templates

---

# REGLA 4 — RESPETAR CONTRATOS DE SERVICIO

Los services existentes son contratos estables.

El LLM no puede:

* cambiar firmas
* cambiar tipos de retorno
* cambiar comportamiento esperado

sin crear nueva versión.

---

# REGLA 5 — NO DUPLICAR DOMINIO

No crear:

* nuevos models duplicados
* nuevos services duplicados

Siempre reutilizar dominio existente.

---

# REGLA 6 — NO REFACTORIZACIONES MASIVAS

Prohibido:

* rewrites completos
* mover múltiples módulos sin razón crítica

Cambios deben ser incrementales.

---

# REGLA 7 — TODO CAMBIO DEBE SER COMPATIBLE CON TESTS

Antes de finalizar cambios, el LLM debe garantizar:

pytest → 100% passing

---

# REGLA 8 — CAPABILITIES SON LA UNICA FORMA DE AUTORIZACION

Nunca introducir autorización basada en:

* role name
* role id
* strings hardcodeados

Solo capabilities.

---

# REGLA 9 — MULTI-TENANT ES OBLIGATORIO

Toda query debe estar filtrada por:

school_id

Nunca retornar datos cross-tenant.

---

# REGLA 10 — NO INTRODUCIR COMPLEJIDAD INNECESARIA

No introducir:

* CQRS
* Event sourcing
* Microservicios

sin requerimiento explícito.

---

# REGLA 11 — EL LLM NO PUEDE ROMPER PRODUCCION

El LLM debe preferir:

* agregar
* extender

en lugar de modificar comportamiento existente.

---

# REGLA 12 — PRIORIDAD ABSOLUTA

Orden de prioridad:

1. integridad de datos
2. seguridad
3. estabilidad
4. mantenibilidad
5. nuevas funcionalidades

Nunca al revés.

---

# CONCLUSION

El LLM actúa como ingeniero dentro de un sistema en producción.

No como arquitecto libre.

Debe respetar arquitectura existente.

---

FIN DEL DOCUMENTO
