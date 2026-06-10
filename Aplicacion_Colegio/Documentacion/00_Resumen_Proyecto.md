# Resumen Tecnico del Proyecto - Aplicacion_Colegio

Fecha de referencia: 12-03-2026.

## 0. Contexto operativo actual (que estamos haciendo)

Estado del trabajo en curso:
- Estabilizacion del dashboard y vistas por rol (especialmente estudiante) para eliminar errores de render y regresiones funcionales.
- Cierre de brechas entre codigo legacy (templates Django) y contratos nuevos de API v1.
- Endurecimiento de CI: primero evitar fallos funcionales (tests rojos), luego recuperar umbral de cobertura minimo requerido.
- Consolidacion de seguridad y permisos por capabilities, evitando chequeos acoplados a nombres de rol.

Objetivo de corto plazo:
- Mantener la aplicacion operativa sin romper compatibilidad existente.
- Reducir deuda tecnica de integracion (legacy + v1) con cambios incrementales y trazables.

Reglas de ejecucion que se estan aplicando:
- Cambios pequenos y verificables (test puntual + test relacionado).
- Priorizar fixes de estabilidad antes de refactors grandes.
- No mezclar cambios de infraestructura con cambios funcionales en el mismo commit.

## 0.1 Donde va cada cosa (mapa rapido de carpetas)

Raiz del repo:
- manage.py: entrypoint Django para comandos locales (runserver, migrate, shell, etc.).
- config/settings.py: configuracion principal del proyecto para entorno raiz.
- backend/: dominio backend principal (apps, servicios, reglas de negocio, API).
- frontend/templates/: vistas Django por modulo y por rol.
- frontend/static/: assets estaticos (css/js/imagenes) usados por templates.
- frontend-react/: frontend React (Vite) para pantallas nuevas o migradas.
- tests/: suite principal de pruebas (unit, integration, functional, regression).
- scripts/: utilidades operativas (tests, migraciones, auditorias).
- docs/: contratos y documentos de arquitectura/seguimiento.

Carpeta anidada Aplicacion_Colegio/:
- Replica operativa del proyecto usada en algunos flujos/localizaciones de CI.
- Debe mantenerse alineada con la raiz si se utiliza como fuente de ejecucion.
- Si aparece divergencia entre raiz y carpeta anidada, pueden ocurrir fallos inconsistentes en CI.

## 0.2 Que hace cada capa del sistema

Backend Django:
- backend/apps/*/models.py: define entidades y estructura de datos.
- backend/apps/*/services/: concentra logica de negocio (reglas, calculos, orquestacion).
- backend/apps/*/views/: adaptadores HTTP (toman request, llaman servicios, devuelven response).
- backend/apps/api/: endpoints versionados para consumo frontend/movil.

Frontend templates (server-rendered):
- frontend/templates/dashboard.html: contenedor principal del dashboard por rol.
- frontend/templates/sidebars/: navegacion lateral por tipo de usuario.
- frontend/templates/<modulo>/: vistas funcionales por dominio (academico, matriculas, etc.).

Frontend React (cliente SPA parcial):
- frontend-react/src/features/: funcionalidades agrupadas por dominio/rol.
- frontend-react/src/shared/: componentes y utilidades transversales.
- vite.config.js: build/dev server del frontend React.

Testing y calidad:
- tests/unit/: validacion de funciones, servicios y reglas aisladas.
- tests/integration/: validacion de integracion entre componentes (DB, auth, API).
- tests/functional/: validacion de flujos de usuario y respuestas de vistas.
- tests/regression/: pruebas de no regresion sobre rutas/operaciones criticas.

Documentacion operativa:
- docs/API_CONTRACT_*.md: contratos de entrada/salida esperados por frontend.
- docs/SEGUIMIENTO_*.md: bitacoras tecnicas de cambios y decisiones.
- REGLAS_PROYECTO.md: criterios de trabajo y restricciones tecnicas del repo.

## 1. Instalacion del proyecto desde cero

### 1.1 Requisitos base
- Python >= 3.12
- Git
- Entorno local: SQLite (por defecto)
- Entorno recomendado de integracion: Docker + Docker Compose

### 1.2 Instalacion local (modo desarrollo)
```bash
git clone <url-del-repositorio>
cd Aplicacion_Colegio

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

URL local:
- http://127.0.0.1:8000

### 1.3 Despliegue local reproducible con Docker
```bash
docker compose up --build
```

Servicios:
- Web ASGI (Daphne): localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

Migraciones en contenedor:
```bash
docker compose exec web python manage.py migrate
```

## 2. Caracteristicas tecnicas del proyecto

- Backend basado en Django 5.x con estructura modular por apps.
- API REST versionada y extensible bajo prefijo api/v1.
- Capa de autorizacion por capabilities con PolicyService (fuente unica de permisos).
- Arquitectura multi-tenant: aislamiento por colegio en consultas y servicios.
- Soporte asincrono y tiempo real con ASGI + Channels + Redis.
- Convivencia controlada entre endpoints legacy y endpoints nuevos.
- Frontend dual:
	- Django templates para vistas existentes.
	- Frontend React (Vite) para nuevas interfaces.
- Pipeline de testing y calidad con pytest, pytest-django y flake8.

## 3. Descripcion tecnica del dominio

Aplicacion_Colegio es una plataforma SaaS de gestion escolar orientada a Chile. El sistema integra modulos academicos, administrativos y financieros con foco en seguridad, escalabilidad funcional y evolucion incremental.

Objetivos de arquitectura:
- Evitar logica de negocio en vistas.
- Centralizar reglas de autorizacion.
- Mantener compatibilidad hacia atras durante migraciones funcionales.
- Sostener integridad de datos bajo escenarios multi-colegio.

## 4. Puntos de interes tecnico

### 4.1 Seguridad y permisos
- Eliminacion progresiva de autorizacion por rol hardcodeado.
- Enforcement por capability para operaciones criticas.

### 4.2 Multi-tenant
- Filtro obligatorio por identificador de colegio.
- Prevencion de fuga de datos entre tenants como criterio de primer nivel.

### 4.3 Estrategia de evolucion
- Cambios incrementales en lugar de refactor masivo.
- Contratos API estables para frontend y cliente movil.

### 4.4 Contexto mercado Chile
- Roadmap con iniciativas especificas (UTP, SEP, alertas tempranas, certificados verificables, libro digital).

## 5. Lenguajes, frameworks y APIs utilizadas

### 5.1 Lenguajes
- Python
- JavaScript
- SQL
- HTML/CSS

### 5.2 Frameworks y librerias principales
- Django
- Django REST Framework
- Channels
- Daphne
- channels-redis
- React 18
- Vite
- React Router
- pytest / pytest-django

### 5.3 Servicios e integraciones
- PostgreSQL (produccion recomendada)
- SQLite (desarrollo rapido)
- SQL Server (escenarios corporativos Windows/AD)
- Redis (canales y eventos en tiempo real)
- SMTP (correo transaccional)

### 5.4 APIs y contratos relevantes
- API versionada: /api/v1
- Dashboard API: GET /api/v1/dashboard/resumen/
- Contrato de dashboard con scope dinamico: auto, self, school, analytics, global
- Autenticacion API en consolidacion con JWT (token, refresh, verify, logout)

### 5.5 Modulos backend existentes (Django apps)
- academico
- accounts
- api
- auditoria
- comunicados
- core
- cursos
- institucion
- matriculas
- mensajeria
- notificaciones
- security
- subscriptions

### 5.6 Modulos frontend existentes

Frontend Django templates (frontend/templates):
- academico
- admin
- admin_escolar
- apoderado
- asesor_financiero
- bibliotecario_digital
- compartido
- comunicados
- coordinador_academico
- estudiante
- inspector_convivencia
- matriculas
- mensajeria
- profesor
- psicologo_orientador
- sidebars
- soporte_tecnico_escolar

Frontend static (frontend/static):
- academico
- asesor_financiero
- css
- js
- mensajeria

Frontend React features (Aplicacion_Colegio/frontend-react/src/features):
- admin_escolar
- apoderado
- asesor_financiero
- auth
- bibliotecario_digital
- coordinador_academico
- dashboard
- estudiante
- inspector_convivencia
- profesor
- psicologo_orientador
- soporte_tecnico

## 6. Estado general del proyecto

### 6.1 Estado actual
El proyecto presenta una base arquitectonica madura y funcional, con frentes activos de hardening para salida productiva de mayor escala.

### 6.2 Avances consolidados
- Fundamentos de seguridad definidos y aplicados en la arquitectura.
- Multi-tenant operativo como restriccion transversal.
- Modulos nucleares academicos y financieros implementados.
- Contrato de dashboard v1 documentado para consumo frontend.
- Base de despliegue Docker y CI automatizable disponible.

### 6.3 Trabajo en curso
- Correcciones de vistas y contexto de estudiante.
- Consolidacion de CRUD API faltantes en administracion escolar.
- Cierre de autenticacion JWT end-to-end para cliente movil.
- Implementacion productiva de notificaciones multicanal (web, push, email, realtime).

### 6.4 Riesgo tecnico principal
- Riesgo de regresion por convivencia legacy + api/v1.

Mitigacion activa:
- Validacion por tests.
- Cambios incrementales.
- Respeto estricto de contratos existentes.

## 7. Conclusiones tecnicas

La direccion del proyecto es correcta desde el punto de vista de arquitectura y producto. La prioridad actual es terminar la consolidacion de APIs, autenticacion y notificaciones sin romper compatibilidad operativa, manteniendo seguridad y aislamiento tenant como criterios no negociables.

## 8. Guia de ubicacion por tarea (uso rapido)

Si la tarea es de permisos/autorizacion:
- Revisar backend/apps/*/services/ y PolicyService (capabilities).

Si la tarea es de dashboard o navegacion por rol:
- Revisar frontend/templates/dashboard.html y frontend/templates/sidebars/.
- Revisar backend/apps/core/services/dashboard_*.py para contexto y datos.

Si la tarea es de API para cliente movil/frontend React:
- Revisar backend/apps/api/ y docs de contrato en docs/API_CONTRACT_*.md.

Si la tarea es de estilos o comportamiento visual en templates:
- HTML en frontend/templates/ y assets en frontend/static/css o frontend/static/js.

Si la tarea es React:
- Implementar en frontend-react/src/features/<modulo> y validar build con Vite.

Si la tarea es de calidad o regresion:
- Crear/ajustar pruebas en tests/ segun nivel (unit/integration/functional/regression).

## 9. Contexto de mantenimiento inmediato

Checklist antes de subir cambios:
- Confirmar que no haya diferencias criticas entre raiz y carpeta anidada Aplicacion_Colegio/ si ambas participan en ejecucion.
- Ejecutar al menos test puntual del fix y una corrida relacionada por modulo.
- Validar que no se rompa cobertura minima global exigida por CI.
- Registrar el avance tecnico en un documento de seguimiento cuando el cambio sea sensible.

## 10. Contexto de proyecto para trabajo con LLM

Este proyecto se encuentra en una etapa de consolidacion tecnica donde conviven componentes legacy y componentes nuevos. Por eso, una LLM debe operar con foco en continuidad operativa, seguridad y trazabilidad de cambios.

Prioridades del contexto actual:
- Estabilidad funcional en rutas criticas de dashboard y vistas por rol.
- Compatibilidad entre templates Django existentes y API v1 para frontend moderno.
- Enforzamiento de permisos por capabilities, no por reglas hardcodeadas de rol.
- Aislamiento tenant como restriccion obligatoria en consultas y servicios.
- Cumplimiento de pipeline CI (tests, lint, cobertura minima).

Principio rector:
- Cualquier mejora debe preservar comportamiento esperado en produccion antes de optimizar estructura interna.

## 11. Reglas para el avance de una LLM en este proyecto

### 11.1 Reglas de planificacion
- Antes de implementar, definir alcance acotado y criterio de exito verificable.
- Preferir cambios incrementales (small batch) sobre refactors amplios.
- Evitar tareas mixtas en un mismo avance: separar bugfix, refactor y documentacion.

### 11.2 Reglas de implementacion
- No introducir logica de negocio en vistas si existe capa de servicios.
- Reutilizar servicios existentes antes de crear nuevos puntos de logica.
- Mantener compatibilidad de contratos API y estructura de respuestas esperadas.
- Respetar convenciones actuales de nombres y organizacion por modulo.

### 11.3 Reglas de seguridad y permisos
- Validar siempre permisos por capability en operaciones sensibles.
- Evitar bypass de tenant: toda consulta debe quedar acotada por colegio cuando aplique.
- No exponer informacion sensible en respuestas, logs o mensajes de error.

### 11.4 Reglas de pruebas y calidad
- Cada cambio funcional debe tener al menos una prueba asociada o ajuste de prueba existente.
- Ejecutar como minimo: test puntual del fix + set relacionado por modulo.
- Si el cambio impacta rutas criticas, incluir prueba de regresion.
- Verificar cobertura global para no degradar el umbral definido en CI.

### 11.5 Reglas de trazabilidad
- Documentar brevemente que se cambio, por que, y como se valido.
- Registrar decisiones tecnicas relevantes en docs de seguimiento.
- Mantener mensajes de commit claros, orientados a intencion y resultado.

### 11.6 Reglas de coordinacion con carpeta anidada
- Confirmar si la ejecucion local/CI usa raiz del repo o carpeta anidada Aplicacion_Colegio/.
- Evitar divergencia entre ambas estructuras cuando ambas participan en despliegue o testing.
- Revisar y resolver de inmediato cualquier marcador de conflicto de merge antes de ejecutar CI.

## 12. Flujo recomendado de trabajo asistido por LLM

1. Identificar problema y delimitar alcance.
2. Localizar archivos/capas afectadas segun mapa del proyecto.
3. Aplicar cambio minimo viable.
4. Ejecutar validaciones tecnicas (tests relevantes).
5. Revisar impactos colaterales (permisos, tenant, contratos).
6. Documentar avance y preparar entrega.

Checklist rapido previo a push:
- El cambio corrige la causa raiz y no solo el sintoma.
- No hay conflictos de merge ni artefactos temporales.
- Tests del area pasan localmente.
- El cambio mantiene compatibilidad operativa.
