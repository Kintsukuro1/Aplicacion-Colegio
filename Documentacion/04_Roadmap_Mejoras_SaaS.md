# Roadmap de Mejoras y Evolución SaaS: Aplicación_Colegio

Este documento presenta un análisis del mercado actual de plataformas SaaS para gestión escolar (tanto en Chile como a nivel global) y define un plan de acción (*roadmap*) de qué reparar, mejorar y agregar en **Aplicación_Colegio** para posicionarla como una solución competitiva, moderna y escalable.

---

## 1. Análisis del Mercado Actual (2026)

### Plataformas Chilenas (Lirmi, Colegium, Webclass, NotasNet/Syscolnet)
- **Foco Principal:** Alto cumplimiento normativo MINEDUC (Libro de Clases Digital, firmas digitales), integración profunda de la gestión académica con la administrativa, y fuerte énfasis en la comunicación diaria con los apoderados.
- **Diferenciadores Clave:**
  - Canales directos al celular del apoderado para reportar asistencia, notas y comportamiento (modelo Papinotas).
  - Centralización de planificación pedagógica, banco de recursos y evaluación bajo estándares DUA (Diseño Universal para el Aprendizaje).
  - Gestión integral de recaudación y finanzas (mensualidades, cobros).

### Plataformas Globales (PowerSchool, Canvas, Toddle, ManageBac)
- **Foco Principal:** Interoperabilidad total, ecosistemas modulares donde el SIS (Student Information System) y el LMS (Learning Management System) se conectan sin fricciones.
- **Diferenciadores Clave:**
  - APIs abiertas para integrarse con Google Workspace o Microsoft 365.
  - Automatización operativa profunda (admisión 100% digital, creación inteligente de horarios evitando topes).
  - Mapeo curricular avanzado y portafolios de estudiantes.

---

## 2. Roadmap para Aplicación_Colegio

Basado en el análisis de la competencia y priorizando **mejoras funcionales y operativas robustas (más allá de la Inteligencia Artificial)**, se propone el siguiente roadmap dividido en tres fases:

### 🛠️ FASE 1: Reparar y Estandarizar (Corto Plazo - "Core MVP")
*El objetivo es asegurar la estabilidad, los permisos y el cumplimiento normativo básico.*

1. **[REPARAR] Estandarización de Notas (MINEDUC):**
   - Asegurar que todas las vistas (Frontend React) y lógicas (Backend) calculen y rendericen las notas en la escala chilena (1.0 a 7.0), estandarizando la división por 10 para visualización de registros legados.
2. **[REPARAR] Autorización y Routing por Roles:**
   - Corregir de manera definitiva cualquier fuga de vistas entre roles. Un Profesor no debe ver interfaces de Estudiante. Auditar la capa de seguridad en React.
3. **[ESTANDARIZAR] Libro de Clases Digital (Versión 1):**
   - Consolidar el módulo de asistencia y calificaciones para que la base de datos soporte futuras auditorías o firmas digitales, exigidas por la Circular 30 del MINEDUC.
4. **[NUEVO] Registro Básico de Convivencia Escolar:**
   - Crear un módulo donde Inspectores y Docentes puedan registrar anotaciones (positivas/negativas) y atrasos, centralizando la hoja de vida del alumno en un solo lugar.

### 🚀 FASE 2: Mejorar la Experiencia, Gestión y Operación (Mediano Plazo)
*El objetivo es incorporar los módulos que los colegios exigen para administrar toda la institución sin usar planillas Excel.*

1. **[MEJORAR] Portales de Comunicación y Notificaciones:**
   - Integrar un sistema de mensajería omnicanal (Email / Push Notifications) para enviar circulares y reportes automáticos de atrasos e inasistencias a los apoderados.
2. **[NUEVO] Módulo de Planificación Curricular:**
   - Permitir a los profesores subir y compartir planificaciones vinculadas directamente a los Objetivos de Aprendizaje (OA) del MINEDUC.
   - Banco de Rúbricas y Evaluaciones compartidas entre docentes del mismo departamento.
3. **[NUEVO] Gestión de Finanzas y Pagos (Básico):**
   - Panel para el `Admin_Escolar` donde se lleve el control de pagos de mensualidades, cuotas de centro de padres, becas asignadas y estudiantes morosos.
4. **[MEJORAR] Dashboards Analíticos y Módulo del Psicólogo/Orientador:**
   - Expandir las métricas para incluir tasas de inasistencia, atrasos reiterados y cruzar esto con el rendimiento.
   - Dotar al psicólogo de un flujo formal para registrar entrevistas, citaciones a apoderados y seguimiento de casos de bullying (Ley Aula Segura).

### 🌟 FASE 3: Automatización Avanzada e Interoperabilidad (Largo Plazo)
*El objetivo es digitalizar procesos engorrosos de principio a fin, creando un ecosistema completo.*

1. **[AGREGAR] Admisión y Matrícula 100% Online:**
   - Flujo digital donde los apoderados nuevos o antiguos pueden subir certificados (nacimiento, médicos), actualizar fichas familiares y reservar cupos/listas de espera.
   - Firma electrónica simple para contratos de prestación de servicios educacionales.
2. **[AGREGAR] Pasarelas de Pago Integradas:**
   - Conectar el módulo de finanzas con Webpay (Transbank), MercadoPago o Khipu para que el apoderado pague directamente desde la plataforma y la deuda se salde automáticamente en el sistema.
3. **[AGREGAR] Creador de Horarios y Gestión de Recursos Físicos:**
   - Sistema para asignar salas, cruzar disponibilidad de profesores evitando topes de horarios (timetabling) y módulo para que los docentes reserven proyectores, laboratorios o recursos de la biblioteca.
4. **[AGREGAR] Módulo de Salud, Transporte y Comedor:**
   - Registro en la ficha del estudiante de alergias, medicamentos y restricciones alimentarias.
   - Asignación de recorridos de furgones escolares y control de entrega de raciones de JUNAEB o casino particular.
5. **[AGREGAR] Interoperabilidad y APIs Externas:**
   - Sincronización de credenciales y aulas con Google Workspace for Education (Google Classroom) o Microsoft 365.

---

## 3. Conclusión Estratégica

Para que **Aplicación_Colegio** escale como un SaaS indispensable, la ruta más efectiva es abarcar no solo lo académico, sino **la burocracia administrativa y financiera**. 

Al automatizar la **recaudación (pagos online)**, digitalizar la **matrícula (cero papel)**, ofrecer herramientas de **planificación colaborativa** a los docentes y llevar un control estricto de la **convivencia escolar**, la plataforma se vuelve el núcleo operativo del colegio, haciendo que la institución no pueda (ni quiera) operar sin ella.
