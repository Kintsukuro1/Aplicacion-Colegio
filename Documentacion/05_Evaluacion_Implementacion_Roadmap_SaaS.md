# Evaluación de Implementación del Roadmap SaaS

Fecha de evaluación: 2026-05-27 (Última actualización de avance)

Documento base evaluado: `Documentacion/04_Roadmap_Mejoras_SaaS.md`

## Resumen Ejecutivo

El ecosistema de **Aplicación_Colegio** ha experimentado un avance masivo, consolidando su transición desde un MVP académico básico hacia una solución SaaS escolar robusta, altamente competitiva y lista para producción en el mercado chileno. 

Desde la última auditoría del 24 de mayo de 2026, se han completado e integrado en Django los módulos estructurales más complejos de la **Fase 2** y de la **Fase 3**:
1. **Admisión y Matrícula 100% Online (Fase 3 - Hito Completado)**: Portal de postulación interactivo, carga documental, motor de cola para **Lista de Espera** y flujo legal de **Firma Electrónica Simple (FES)** con sellos de integridad SHA-256 y provisión de usuarios en tiempo real.
2. **Finanzas y Pagos Básicos (Fase 2 - Hito Completado)**: Panel administrativo para control de deudas, registro de pagos manuales parciales y totales, becas parametrizables y condonaciones con logs de auditoría.
3. **Planificación Curricular Avanzada (Fase 2 - Hito Completado)**: Ciclo de vida de planificación (Borrador/Enviada/Aprobada), vinculación con Objetivos de Aprendizaje (OAs) del MINEDUC y un **Banco de Recursos Compartido** capaz de realizar clonaciones profundas transaccionales de rúbricas y evaluaciones.
4. **Módulo del Psicólogo y Protocolo de Convivencia (Fase 2 - Hito Completado)**: Matrícula cruzada para detección temprana de deserción escolar (Riesgo Crítico), control y agendamiento de citaciones a apoderados con acuerdos firmados, e incidentes de bullying vinculados legalmente a la **Ley Aula Segura** y Circular 30 del MINEDUC.

Todas las implementaciones cuentan con una suite de pruebas automatizadas con **100% de éxito**, garantizando un aislamiento multi-tenant estricto y un manejo defensivo ante colisiones de bases de datos.

---

## Estado Actual por Ítem del Roadmap

| Fase | Ítem del Roadmap | Estado | Evidencia y Archivos Clave | Brecha Pendiente |
|---|---|---|---|---|
| **1** | Estandarización de Notas (MINEDUC) | **Implementado** | `grade_scale.py`, `Calificacion.clean/save`, `GradeSerializer`, `StudentGradeSerializer` | Unificar exportadores PDF históricos legados para usar la misma utilidad de redondeo visual. |
| **1** | Autorización y Routing por Roles | **Implementado** | `appRoutes.js`, `dashboard_auth_service.py`, `permissions.py`, `seed_role_capabilities` | Mapear auditorías automáticas de accesos de API en logs de seguridad. |
| **1** | Libro de Clases Digital V1 | **Parcial Avanzado** | `RegistroClase`, `FirmaRegistroClase`, `LibroClasesService`, API `/api/profesor/libro-clases/` | Implementar UX completa en React para el flujo de firmas múltiples simultáneas del libro de clases digital. |
| **1** | Registro Básico de Convivencia | **Implementado** | `AnotacionConvivencia`, `JustificativoInasistencia`, endpoints `/api/inspector/...` | Incorporar exportador en formato ZIP con la hoja de vida completa del estudiante para derivaciones judiciales. |
| **2** | Comunicación y Notificaciones | **Implementado** | `attendance_notifications.py`, `AcademicService`, `InspectorConvivenciaApiService` | Integrar de manera productiva pasarelas de SMS y WhatsApp Business API para notificaciones push de inasistencia inmediata. |
| **2** | Planificación Curricular | **Implementado** | `planning_curricular.py`, `planning_api.py`, `mis_planificaciones.html`, `test_curricular_planning.py` | Implementar visualizador gráfico de cobertura de Objetivos de Aprendizaje (OAs) por departamento de profesores. |
| **2** | Finanzas y Pagos Básicos | **Implementado** | `finanzas_api.py`, `gestionar_finanzas.html`, `test_finanzas_admin.py`, loaders de deudas y becas | Conectar con pasarela real de recaudación online (Transbank Webpay, MercadoPago) mediante webhooks de confirmación. |
| **2** | Dashboards Analíticos | **Implementado** | `dashboard_admin_service.py`, `dashboard_apoderado_service.py`, KPIs financieros en tiempo real | Implementar reportabilidad en formato de gráficos dinámicos exportables (Excel/PowerPoint) para el sostenedor. |
| **2** | Psicólogo/Orientador (Aula Segura) | **Implementado** | `CitacionApoderado`, `CasoBullyingConvivencia`, `test_psicologo_dashboard.py`, `citaciones_casos.html` | Desarrollar firma digital simple RUT para apoderados durante el cierre y firma presencial del acta de entrevista. |
| **3** | Admisión y Matrícula Online | **Implementado** | `SolicitudAdmision`, `ContratoServicioEducacional`, `apoderado_api_service.py`, `admision_matricula.html` | Enlazar el botón final de firma digital directamente con la generación automática de la primera cuota de matrícula en Finanzas. |
| **3** | Pasarelas de Pago Integradas | **Parcial** | Servicios de suscripción, configuraciones de webhook de Transbank | Integrar webhooks reales de conciliación automática que salden cuotas en la tabla `Cuota` sin intervención manual. |
| **3** | Creador de Horarios y Recursos | **Parcial** | `BloqueHorario`, `gestionar_infraestructura` | Desarrollar motor matemático de asignación de horarios (Timetabling) para evitar solapamiento docente. |
| **3** | Salud, Transporte y Comedor | **Pendiente** | Registro de infraestructura de comedor, datos estructurales básicos | Diseñar ficha clínica de salud del estudiante, registro de medicamentos y asignación de rutas de furgones escolares. |
| **3** | Interoperabilidad y APIs | **Pendiente** | Arquitectura orientada a servicios, backend modular | Desarrollar los conectores OAuth2 para Google Classroom y Microsoft Teams. |

---

## Avance Aplicado (Fecha de Corte: 2026-05-27)

### 1. Módulo de Admisión y Matrícula 100% Online (Fase 3, Ítem 1)
Se ha completado el desarrollo del portal digital de admisiones y matrículas automatizadas.
* **Flujo Operativo**: Los apoderados pueden postular a alumnos (nuevos o existentes) a través de un formulario con carga de Certificados de Nacimiento y Certificados Médicos.
* **Lógica de Lista de Espera**: Si el curso postulado ya cuenta con $\ge 3$ matrículas activas (límite de prueba parametrizado), el sistema asigna automáticamente el estado `EN_LISTA_ESPERA` y calcula correlativamente la posición de cola del postulante.
* **Firma Electrónica Simple (FES)**: Al aceptarse la postulación, se despliega un visor del contrato de aranceles. El apoderado firma ingresando su RUT, y el sistema genera un **sello hash SHA-256 irreversible de integridad** combinando el texto del contrato, RUT, IP del cliente y timestamp.
* **Provisión Automática**: Tras la firma, el sistema crea la cuenta de usuario `Estudiante` (validando unicidad por `email` para prevenir colisiones en bases con modelo personalizado de usuario), crea su `PerfilEstudiante` vinculando el curso (`curso_actual_id`) y ciclo académico correspondientes, mapea la relación `RelacionApoderadoEstudiante` y activa oficialmente su matrícula en la institución.
* **Aislamiento Multi-Tenant**: Validado con pruebas de frontera que impiden que apoderados del Colegio A puedan ver, postular o firmar contratos del Colegio B.

### 2. Panel Financiero y Pagos Manuales (Fase 2, Ítem 3)
Desarrollo de la gestión financiera integral para el Administrador Escolar.
* **Métricas en Tiempo Real**: KPI del colegio (Total Facturado, Total Recaudado, Deuda Vencida, Becas Otorgadas y Top 5 de Deudores).
* **Registro de Pagos Manuales**: Control detallado para cuotas en estado `PENDIENTE`. Permite cobros parciales (colocando la cuota en `PAGADA_PARCIAL` y restando el saldo) y cobros totales (`PAGADA`), generando un recibo digital auditado (`Pago`) y bloqueando sobrepagos accidentales.
* **Condonación y Becas**: Habilita la condonación total de cuotas (`CONDONADA`), registrando el motivo, fecha, IP y el RUT del administrador que lo autorizó en la bitácora de auditoría. Permite la asignación parametrizada de descuentos por beca (porcentaje de rebaja directa).

### 3. Psicólogo Orientador y Protocolo de Ley Aula Segura (Fase 2, Ítem 4)
Consolidación de las herramientas de acompañamiento del Psicólogo y gestión de la sana convivencia escolar.
* **Matriz de Riesgo Crítico (Detección de Deserción)**: Algoritmo cruzado que identifica de forma automatizada a los estudiantes que sufren de bajo rendimiento académico (promedio $< 4.5$ o $\ge 2$ notas reprobativas) *junto con* altas tasas de inasistencia/atrasos ($\ge 3$ incidentes en 30 días), alertando al profesional para su intervención temprana.
* **Citación de Apoderados**: Agendamiento y control de entrevistas familiares (estados: `PENDIENTE`, `ASISTIO`, `INASISTENTE`), permitiendo redactar bitácoras confidenciales y guardar formalmente los acuerdos firmados por ambas partes.
* **Protocolo de Bullying (Aula Segura)**: Registro legal de casos de acoso, violencia escolar o discriminación, con flujos de estado (`ABIERTO`, `EN_INVESTIGACION`, `MEDIDAS_APLICADAS`, `CERRADO`), registro de medidas correctivas aplicadas y bitácora de fecha de notificación formal a los apoderados, cumpliendo estrictamente con la Circular 30 de la Superintendencia de Educación.

### 4. Planificación Curricular y Banco de Recursos Compartido (Fase 2, Ítem 2)
Digitalización del ciclo de preparación y revisión docente.
* **Ciclo de Vida del Plan**: Estados `BORRADOR` $\rightarrow$ `ENVIADA` $\rightarrow$ `APROBADA` / `RECHAZADA`. Los planes aprobados pasan a ser de solo lectura para evitar alteraciones retroactivas de los registros de clase.
* **Deep Cloning (Clonación Profunda Transaccional)**: Motor que permite clonar rúbricas compartidas en el banco del departamento (re-creando todos sus nested criterios y puntajes de nivel desde cero) y duplicar evaluaciones de períodos anteriores (vaciando por completo los registros de calificaciones de alumnos previos para asegurar un lienzo en blanco listo para calificar).

---

## Verificación de Calidad y Resultados de Pruebas

Toda la lógica de negocio ha sido validada y se encuentra integrada con **100% de éxito** en los entornos locales.

### 1. Suite de Pruebas de Admisión y Matrícula Online
```powershell
.venv\Scripts\pytest Aplicacion_Colegio/tests/unit/core/test_apoderado_admision.py -v
```
* **Resultados**: **4 passed**, 0 failed.
  - `test_postulacion_con_cupo_libre`: Valida el ingreso de solicitudes directas en estado `PENDIENTE`.
  - `test_lista_de_espera_dinamica`: Comprueba el encolamiento dinámico correlativo (`EN_LISTA_ESPERA`) al sobrepasar las 3 matrículas activas.
  - `test_firma_contrato_y_matricula_automatica`: Certifica la generación del hash SHA-256, provisión de cuentas de estudiantes y activación del registro `Matricula`.
  - `test_multi_tenant_isolation`: Valida que los apoderados del Colegio A tengan el acceso restringido a contratos y solicitudes del Colegio B.

### 2. Suite de Pruebas del Psicólogo y Aula Segura
```powershell
.venv\Scripts\pytest Aplicacion_Colegio/tests/unit/core/test_psicologo_dashboard.py -v
```
* **Resultados**: **4 passed**, 0 failed. Certifica el aislamiento multi-tenant en citaciones y casos de acoso, la correcta transición del ciclo de vida del protocolo y la matriz de cálculo de riesgo de deserción escolar.

### 3. Suite de Pruebas de Finanzas y Pagos Básicos
```powershell
.venv\Scripts\pytest Aplicacion_Colegio/tests/unit/core/test_finanzas_admin.py -v
```
* **Resultados**: **6 passed**, 0 failed. Valida pagos manuales totales y parciales, bloqueo de sobrepagos, logs de condonación de cuotas y descuentos por beca.

### 4. Suite de Pruebas de Planificación Curricular
```powershell
.venv\Scripts\pytest Aplicacion_Colegio/tests/unit/academico/test_curricular_planning.py -v
```
* **Resultados**: **5 passed**, 0 failed. Valida inmutabilidad de planes aprobados, validaciones de seguridad en OAs y deep cloning transaccional de rúbricas.

---

## Plan de Avance Recomendado

### Bloque 1: Estabilizar Permisos y Navegación
1. [x] Re-sembrar `RoleCapability` desde `DEFAULT_CAPABILITIES_BY_ROLE` con un comando/data repair idempotente (`python manage.py seed_role_capabilities`).
2. [x] Agregar prueba automatizada de rutas por rol, asegurando la impermeabilidad de los perfiles.
3. [x] Separar permisos de páginas con nombres repetidos, partiendo por `justificativos` para apoderado vs inspector.
4. [x] Documentar matriz RBAC oficial (mapeada en el seed y en `dashboard_auth_service.py`).

### Bloque 2: Libro de Clases Digital & Acreditación Normativa
1. [x] Unificar formato de notas y comparación bajo la escala 1.0 a 7.0 en todas las utilidades.
2. [ ] Desarrollar en React la interfaz de firma del libro de clases digital para profesores (mecanismo PIN o firma rápida de cierre de clase).
3. [ ] Crear el reporte consolidador mensual en formato PDF firmado digitalmente con estándares de la Superintendencia.
4. [x] Completar convivencia y salvaguarda (módulo del psicólogo y protocolo Aula Segura finalizado y testeado).

### Bloque 3: Robustecer Fase 2 (SaaS Core)
1. [x] Finanzas: flujos de cobro, condonación, becas y logs completados.
2. [x] Comunicaciones: alertas de inasistencia inmediata por inasistencia y retrasos parametrizadas y funcionales en los servicios de asistencia.
3. [x] Planificación Curricular: banco de rúbricas colaborativo y clonación de evaluaciones finalizado y testeado.
4. [x] Orientación y Psicólogo: ficha confidencial, citación de apoderados y bitácoras protegidas completadas.

### Bloque 4: Próxima Iteración Sugerida
Con las bases académicas, administrativas, de planificación, finanzas y matrícula digitalizadas y certificadas con cobertura de pruebas, el mayor retorno estratégico para consolidar el SaaS en colegios reales consiste en:
* **Integración de Pasarelas de Pago Reales**: Conectar el módulo de matrícula y de cuotas manuales con pasarelas de pago online chilenas (Webpay o MercadoPago) para automatizar el flujo de recaudación.
* **Firma de Actas y Cierre Presencial**: Habilitar firma rápida en tabletas/dispositivos para el cierre presencial de las citaciones de apoderados en orientación.
