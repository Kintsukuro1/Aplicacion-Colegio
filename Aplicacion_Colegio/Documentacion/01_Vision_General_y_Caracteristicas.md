# 1. Visión General y Características Principales

## Visión General de la Plataforma
Aplicacion_Colegio es una plataforma escolar SaaS diseñada para operar bajo un modelo **multi-tenant** (cada colegio opera aislado con su propio contexto y datos). 
El stack tecnológico combina la solidez de **Django y Django Rest Framework (DRF)** en el backend, con una transición progresiva hacia **React 18 y Vite** en el frontend.

### ¿Por qué esta arquitectura híbrida (Legacy + React)?
* **Implementación:** Conviven pantallas nuevas en React con vistas legacy renderizadas desde templates de Django (HTML, CSS y JS Vanilla).
* **Elección y Razón:** Se eligió este enfoque para permitir una **migración progresiva** (estrategia del estrangulador). Los módulos core estables continúan funcionando de manera confiable con el stack legacy, mientras que las interfaces que requieren alta interactividad y dinamismo se construyen en React. Esto mejora drásticamente la experiencia del usuario (UX) sin paralizar la entrega de nuevas funcionalidades durante la migración.

---

## Características Principales y Decisiones de Diseño

### 1. Dashboard y Analítica
* **Característica:** Sistema de KPIs, gráficos interactivos (Chart.js), tarjetas de resumen y alertas personalizadas según el rol en sesión (Administrador, Profesor, Apoderado).
* **Elección de Diseño:** La carga de datos de los widgets se realiza de forma asíncrona mediante APIs (ej. `/api/v1/dashboard/resumen/`) en lugar de renderizar la data inicial desde el servidor en una sola vista masiva.
* **Razón:** Esto evita bloqueos en la carga inicial de la página. El usuario visualiza la estructura de la aplicación de inmediato y los widgets se llenan a medida que los datos están listos, mejorando considerablemente el rendimiento percibido y reduciendo la carga del servidor en solicitudes complejas.

### 2. Gestión Académica y Biblioteca
* **Característica:** Control integral de clases, asistencia, calificaciones, y gestión de recursos de biblioteca (préstamos, devoluciones).
* **Elección de Diseño:** Toda la lógica pesada de negocio está centralizada en la capa de `services` (ej. `backend/apps/academico/services.py`) y nunca acoplada directamente en las vistas o serializadores.
* **Razón:** Fomenta la escalabilidad y reutilización de código. Una regla como "calcular promedio final" puede ser ejecutada desde un endpoint REST, un comando interno de terminal o una vista legacy, usando exactamente el mismo bloque de código y facilitando las pruebas unitarias.

### 3. Calendario Escolar y de Alumno
* **Característica:** Visualización interactiva de eventos, tareas y entregas mensuales y diarias.
* **Elección de Diseño:** El calendario del alumno se construyó **desde cero** utilizando un template de Django, CSS y JavaScript Vanilla, inyectando los datos como JSON estático inicial y manipulando la UI mediante modales.
* **Razón:** Se optó por no usar librerías de terceros pesadas (como FullCalendar) porque se necesitaba un control estricto sobre el diseño visual y las interacciones específicas exigidas por el colegio. Además, esto mantiene el tamaño de los archivos (bundle) sumamente ligero para asegurar una carga instantánea incluso en conexiones a internet deficientes.

### 4. Portal de Apoderado, Comunicados y Reuniones
* **Característica:** Espacio dedicado para que los tutores revisen notas, justifiquen inasistencias, soliciten reuniones y reciban comunicaciones oficiales.
* **Elección de Diseño:** El control de acceso está sustentado en un sistema de **Capabilities (Capacidades granulares)**, desvinculando la seguridad de los clásicos "Roles".
* **Razón:** En el ecosistema escolar, un usuario puede ser simultáneamente "Profesor" de una clase y "Apoderado" de un alumno. Validar accesos evaluando si el usuario posee la capacidad técnica (ej. `can_view_student_grades`) resuelve los conflictos de multi-rol y asegura que los usuarios solo accedan a lo que estrictamente les corresponde.

### 5. Finanzas e Importación/Exportación Masiva
* **Característica:** Manejo de cuotas, becas, generación de estados de cuenta y procesos de carga masiva mediante archivos CSV/XLSX.
* **Elección de Diseño:** Procesos aislados que operan en transacciones de base de datos (`transaction.atomic` en Django) apoyados en plantillas estandarizadas.
* **Razón:** La importación de registros y la gestión financiera exigen máxima fiabilidad. Aislar estas tareas garantiza que si falla una fila de un CSV o un cálculo de beca, se reviertan los cambios en bloque (rollback) previniendo estados inconsistentes o pérdida de dinero.
