# 2. Arquitectura, Interacciones y Flujos Críticos

Este documento detalla cómo los distintos engranajes de la aplicación interactúan entre sí y cómo están diseñados los flujos que soportan el uso diario del colegio.

---

## Arranque y Estructura Base
El sistema se inicializa utilizando `manage.py`, apoyándose en las configuraciones declaradas en `backend.apps.core.settings`. Las rutas maestras están orquestadas centralizadamente desde `backend/apps/core/urls.py`.

* **Elección de Base de Datos:** Uso de SQLite para el entorno de desarrollo y PostgreSQL para producción.
* **Razón:** Se tomó esta decisión para agilizar drásticamente la integración de nuevos desarrolladores. Pueden clonar y correr el proyecto en minutos sin configurar servidores locales de DB, mientras que el ORM de Django asegura que las consultas funcionen de manera equivalente y segura en el PostgreSQL productivo.

---

## ¿Cómo interactúan las capas del sistema?

La arquitectura establece una separación estricta de responsabilidades entre el Cliente (Frontend) y el Servidor (Backend).

### 1. El Frontend (Consumidor de Datos)
Tanto las interfaces legacy (JavaScript Vanilla usando `fetch`) como el ecosistema moderno (React usando `Axios` o `TanStack Query`) operan bajo un paradigma de UI "tonta". Su única misión es solicitar datos, renderizar componentes visuales e interceptar los clics del usuario.
* **Elección de Service Worker:** Se configuró el `service-worker.js` para **cachear exclusivamente activos estáticos** (CSS, imágenes, JS empaquetado).
* **Razón:** Se bloqueó intencionalmente el almacenamiento en caché de las rutas `/api/...`. En un colegio, las notas, asistencias y pagos cambian en tiempo real. Cachear estas peticiones provocaría que un profesor vea información obsoleta (ej. un alumno "ausente" que ya fue justificado), causando problemas administrativos graves.

### 2. El Backend (Procesador y Fuente de Verdad)
Es responsable absoluto de la seguridad, validación de reglas de negocio, y persistencia de información.
* **Elección de Diseño (Capa de Servicios):** Se delegó toda la lógica compleja a `services` y `helpers` específicos por módulo.
* **Razón:** Esto impide que las Vistas (Views) o serializadores engorden innecesariamente (evitando el antipatrón de "Fat Controllers"). Hace que el backend sea modular y altamente testeable.

---

## Flujos Operativos Críticos

A continuación, se explica el por qué del comportamiento en los flujos más sensibles.

### 1. Flujo de Autenticación (`backend/common/utils/view_auth.py`)
* **Proceso:** Login, validación de credenciales y autorización de navegación según rol.
* **Elección de Diseño:** La plataforma ofrece soporte **Dual**: maneja estado por **Sesión tradicional** (Cookie) y mediante **Tokens JWT** (JSON Web Tokens).
* **Razón:** Esta flexibilidad es obligatoria por la naturaleza híbrida del proyecto. Las páginas legacy confían en la seguridad blindada de la sesión de Django, mientras que la SPA de React y los módulos desacoplados pueden autorizarse a través de JWT sin depender de las limitaciones de las cookies cruzadas.

### 2. Flujo de Protección de Acciones y Seguridad
* **Proceso:** Endpoints expuestos al público o acciones destructivas/financieras (login, cambio de clave, creación de usuarios).
* **Elección de Diseño:** Implementación cruzada de *Capabilities*, token de mitigación CSRF y la integración de **hCaptcha** (`backend/common/utils/captcha.py`).
* **Razón:** Una escuela es un blanco fácil para ataques de fuerza bruta o envíos masivos de spam por formularios. Incorporar validación de captcha a nivel de backend detiene la automatización antes de tocar la base de datos, mientras que las *capabilities* blindan las rutas internas ante manipulaciones intencionadas.

### 3. Sincronización en Tiempo Real
* **Proceso:** Entrega de notificaciones instantáneas, mensajes de chat y confirmación de aprobaciones de reunión.
* **Elección de Diseño:** Implementación del protocolo **WebSockets** a través del endpoint `ws/notificaciones/`.
* **Razón:** Se descartó el uso de *Polling* tradicional (donde el navegador pregunta al servidor "¿hay mensajes nuevos?" cada pocos segundos) porque consumiría todos los recursos del servidor con miles de usuarios activos. Los WebSockets mantienen una tubería abierta eficiente, donde el servidor simplemente "empuja" el aviso al cliente solo cuando sucede, logrando escalabilidad y menor latencia.
