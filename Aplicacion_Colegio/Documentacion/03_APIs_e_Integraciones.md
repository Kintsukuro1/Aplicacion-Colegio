# 3. APIs e Integraciones de Terceros

Este documento consolida el mapa de servicios que sustentan la comunicación del proyecto y explica por qué se integraron proveedores externos específicos.

---

## Servicios e Integraciones Externas

El uso de APIs de terceros se ha delimitado estrictamente a delegar problemas de alta especialización técnica o legal, como lo son la seguridad perimetral y el procesamiento de dinero.

### 1. Prevención de Bots (hCaptcha)
* **Ubicación:** Centralizado en `backend/common/utils/captcha.py`.
* **Elección y Razón:** Se eligió **hCaptcha** en lugar de Google reCAPTCHA o soluciones en casa. hCaptcha ofrece un fuerte compromiso con la privacidad (cumple estrictamente GDPR/leyes de datos) al no rastrear pasivamente el historial de navegación del usuario, y ofrece un nivel de desafío robusto para proteger los portales públicos del colegio contra ataques automatizados de denegación o fuerza bruta.

### 2. Ecosistema de Pagos (Webpay/Transbank y MercadoPago)
* **Uso:** Gestión de pagos para matrículas, mensualidades y servicios financieros de asesoría.
* **Elección de Diseño:** La integración no se realiza esperando una respuesta síncrona, sino mediante el patrón asíncrono de **Webhooks** (callbacks inversos) apuntando a `/api/v1/payments/webhook/`.
* **Razón:** Procesar pagos es impredecible. Si un apoderado pierde conexión en medio de un pago, el colegio no puede perder ese registro. Con Webhooks, una vez que Transbank o MercadoPago finalizan el cobro internamente, son ellos quienes envían una petición segura y certificada al backend de la escuela. El servidor entonces valida las firmas, cambia la cuota a estado "Pagada" y envía el recibo, independientemente de si el apoderado cerró su navegador.

### 3. Herramientas de Auditoría (Django Debug Toolbar)
* **Elección y Razón:** Configurado **única y exclusivamente** para entornos de desarrollo. Su integración fue decidida para proveer a los programadores métricas exactas del tiempo de respuesta y redundancia de las consultas SQL generadas por el ORM, asegurando un monitoreo preventivo de cuellos de botella ("Problema N+1") antes de llegar a los colegios.

---

## Mapa Central de APIs Internas (RESTful)

Las APIs propias actúan como el pegamento indispensable entre las interfaces visuales (React y templates) y los motores de bases de datos. Mantener esta arquitectura centralizada garantiza que a futuro pueda conectarse una aplicación móvil sin escribir lógica desde cero.

### Endpoints Estructurales
* **Autenticación:** `/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`, `/api/v1/auth/logout/` y `/api/v1/me/`. Manejan la creación, vida y destrucción segura de las sesiones.
* **Dashboard:** `/api/v1/dashboard/resumen/...`. Emite payloads JSON con tarjetas estadísticas ligeras.
* **Onboarding Escolar:** `/api/v1/onboarding/...`. Rutas de uso exclusivo para crear colegios nuevos (multi-tenant) e inyectar datos falsos iniciales para demostraciones comerciales.

### Endpoints por Módulo de Negocio
* **Área Académica:** `/api/v1/estudiante/...` y las rutas legacy `/estudiante/...`. Exponen listados de asistencia, calificaciones y reportes en formato inmutable para asegurar que el frontend no pueda alterar notas.
* **Portal del Apoderado:** `/api/v1/apoderado/...`. Gestiona la vinculación de relaciones de tutela (pupilos) y firma electrónica de permisos escolares.
* **Biblioteca Digital:** `/api/bibliotecario/...`. Resuelve la disponibilidad de libros, reserva y asignación de préstamos.
* **Centro Financiero:** `/api/asesor-financiero/...`. Emite boletas, deudas consolidadas y estados de cuenta estructurados de cada familia.
* **Exportador y Procesador:** `/api/importacion/...` y `/api/exportacion/...`. Permiten alimentar la base de datos descargando e inyectando plantillas pre-formateadas de Excel.

### Comunicación Asíncrona Interna
* **Notificaciones en Vivo:** `ws/notificaciones/`. Socket canalizador de avisos en tiempo real. Actúa en equipo junto al endpoint `/api/v1/notificaciones/...` (el cual permite al usuario leer el histórico si estaba desconectado cuando la notificación se emitió).

### Recomendación de Lectura para Auditores Técnicos
1. Se sugiere inspeccionar primero el módulo de **Autenticación**.
2. Seguir con el flujo del **Dashboard** para entender cómo se enrutan los permisos.
3. Analizar la lógica delegada a los **Services** dentro del submódulo de interés.
