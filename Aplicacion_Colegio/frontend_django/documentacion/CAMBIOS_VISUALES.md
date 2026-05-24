

**Fecha:** 2026-05-18  
**Alcance:** `Aplicacion_Colegio/frontend_django` — solo HTML y CSS  
**Sin cambios en:** views, urls, modelos, `frontend-react/`

---

## Resumen

Se aplicó una **identidad visual pastel** al portal académico Django: se eliminó el naranja intenso, se unificó el acceso al login y se alinearon la landing, el login y el dashboard interno (navbar, sidebar, tarjetas) con la misma paleta.

Objetivo: portal moderno, suave y consistente (navbar rosa, sidebar rosa, tarjetas lila/amarillo, botones salmón).

---

## Paleta global (`:root`)

Definida en `static/css/design-system.css` y reutilizada en `index.css` y `login.css`:

| Variable | Color | Uso |
|----------|-------|-----|
| `--color-primary` | `#E8967A` | Botones, acentos, badges |
| `--color-secondary` | `#C084A0` | Hover, enlaces, gradientes |
| `--color-background` | `#FDF8F0` | Fondo general (crema) |
| `--color-navbar` | `#FFE4E4` | Barra superior y footer landing |
| `--color-card` | `#E8E4FF` | Tarjetas / bloques lila |
| `--color-card-yellow` | `#FFF9E6` | Tarjetas destacadas |
| `--color-success` | `#E8F5F0` | Avisos positivos |
| `--color-text` | `#3D3D3D` | Texto principal |
| `--color-text-light` | `#7A7A7A` | Texto secundario |
| `--color-border` | `#F0E0E0` | Bordes suaves |
| `--color-white` | `#FFFFFF` | Superficies |

**Reemplazo masivo en CSS:** tonos como `#ff8a00`, `#f97316`, `#f59e0b`, `#ea580c`, `#fd7e14`, etc. pasaron a `var(--color-primary)` o variantes de la paleta en los archivos bajo `static/css/`.

---

## 1. Página de inicio (HOME)

**Plantilla:** `templates/index.html`  
**Estilos:** `static/css/index.css`

| Cambio | Detalle |
|--------|---------|
| Paleta pastel | Fondo crema, navbar rosa, sin naranja fuerte |
| Un solo acceso | Un botón «Ingresar al Portal» en navbar y hero; eliminados «Postular Ahora» y doble login (estudiantes vs personal) |
| Carrusel | 5 imágenes en `static/img/pwa/`: `escolares.avif`, `EscolarPortada.jpg`, `grupo.avif`, `niña.avif`, `patio.jpg` — autoplay, flechas y puntos |
| Portal unificado | Sección `#portal` con una tarjeta y un enlace a `accounts:login` |
| Tipografía | Plus Jakarta Sans |
| Botones | Bordes redondeados (~14px) |
| Footer | Logo EduHub con gradiente pastel (rosa → lila) |

**Cache busting CSS:** `index.css?v=20260518`

---

## 2. Login unificado

**Plantilla:** `templates/login.html`  
**Estilos:** `static/css/login.css`

| Antes | Después |
|-------|---------|
| Pestañas Estudiante / Apoderado | Un solo formulario para todos los roles |
| Marca «EduConnect» | **EduHub** |
| Fondo gris / naranja | Fondo `var(--color-background)`, tarjeta centrada con sombra suave |
| Campo según rol | Etiqueta genérica: «Usuario o correo electrónico» |

El backend sigue usando la misma URL y acción (`accounts:login`); la detección de rol queda del lado del servidor (no se modificó Python).

**Nota:** `templates/login_staff.html` y `login_staff.css` no se rediseñaron en esta pasada; la landing ya no enlaza al login de personal por separado.

**Cache busting CSS:** `login.css?v=20260518`

---

## 3. Portal interno (dashboard y componentes)

**Archivos principales:**

- `static/css/design-system.css` — variables globales
- `static/css/dashboard.css` — sidebar, header, tarjetas, fondos
- `static/css/components.css` — botones y banners (gradientes salmón–lila)

| Elemento | Estilo aplicado |
|----------|-----------------|
| `body` / contenido | Fondo crema (`--color-background`) |
| `.sidebar` | Gradiente rosa pastel (`--color-navbar`) |
| `.top-header` | Navbar rosa pastel |
| Enlaces activos sidebar | Fondo lila (`--color-card`), borde salmón |
| `.card` | Bordes suaves, sombra pastel |
| `.stat-card` | Fondo amarillo pastel (`--color-card-yellow`) |

El resto de CSS por módulo (profesor, estudiante, admin_escolar, etc.) hereda colores vía variables donde ya se reemplazó el naranja.

---

## Archivos tocados (referencia rápida)

### Plantillas HTML

- `templates/index.html` — landing + carrusel + portal único
- `templates/login.html` — login unificado

### CSS (principales)

- `static/css/design-system.css`
- `static/css/index.css`
- `static/css/login.css`
- `static/css/dashboard.css`
- `static/css/components.css`
- Resto de `static/css/**/*.css` — sustitución de hex naranjas por variables

### Imágenes (solo referenciadas, no movidas)

- `static/img/pwa/*` — carrusel del home

---

## Cómo verificar

1. Levantar Django: `python manage.py runserver`
2. Abrir la raíz del sitio: landing con carrusel y un solo CTA de login
3. Ir a login: formulario único, fondo crema, sin pestañas de rol
4. Entrar con un usuario de prueba: sidebar/header en tonos rosa pastel y tarjetas acordes a la paleta
5. Recarga forzada si no se ven estilos: **Ctrl+F5** (query `?v=20260518` en index y login)

---

## Reglas respetadas en esta entrega

- Solo `templates/` y `static/css/` (más referencias a imágenes existentes)
- No se crearon carpetas nuevas de código (solo esta carpeta `documentacion/`)
- No se modificó `frontend-react/`
- No se tocó lógica Python

---

## Próximos pasos visuales (opcional)

- Alinear `login_staff.html` con el mismo diseño que `login.html` o redirigir al login único
- Revisar páginas con CSS muy específico que aún usen fondos `#fff4ed` u otros restos locales
- Añadir entradas nuevas en este archivo (o `CAMBIOS_VISUALES_YYYY-MM-DD.md`) por cada iteración visual

---

## Dashboard alumno — sidebar unificado y inicio  (2026-05-23)

### Archivos nuevos
- `templates/estudiante/_sidebar.html` — navegación por secciones (Académico / Rendimiento / Comunicación)
- `templates/estudiante/_alumno_wrap_start.html` / `_alumno_wrap_end.html` — layout + CSS `dashboard_alumno.css`

### Paletas por rol (`design-system.css`)
- `body.vista-alumno` → celeste (`--rol-primary`, `--rol-sidebar`, `--rol-accent`)
- `body.vista-apoderado` → verde
- `body.vista-personal` → violeta

### Páginas con sidebar alumno
Inicio, Mis Clases, Mi Horario, Tareas Pendientes (`tareas.html`), Calendario, Mis Tareas, Evaluaciones, Calificaciones, Asistencia, Comunicados, Mensajes.

### Inicio estudiante
- Hero celeste con métricas (borde superior 3px por tipo)
- Timeline vertical con filtro (JS mínimo)
- Accesos rápidos: Mis Clases / Tareas / Calendario

### Cache busting
- `dashboard_alumno.css?v=20260523`

### Mis Clases alineada a Inicio (2026-05-26)
- `estudiante/mis_clases.html` + `estudiante/mis_clases.css`: hero, grid 70/30, cards compactas con franja de color fija, panel evaluaciones y horario de hoy.

### Ajustes inicio (2026-05-23)
- Timeline sin texto `{% cycle %}` suelto; solo badges CLASE/TAREA/etc.
- Métricas con colores #5ba8d4 / #f97316 / #22c55e / #8b5cf6 y barras de progreso
- Secciones: Clases de hoy, Próximas evaluaciones, cards blancas
- Fondo página `#f8fafc`; sidebar blanco con separadores

### Verificación
1. Login como estudiante → `?pagina=inicio`
2. Navegar por el menú lateral en cada sección
3. Ctrl+F5 si no carga el CSS

---

## Portal estudiante — vistas recientes (2026-05-24)

> Bloque de trabajo del portal alumno: **HTML/CSS + backend** en perfil y comunicados. Otras páginas del mismo estilo (hero `mc-` / `ma-` / `mm-`) se hicieron en la misma línea visual.

### Resumen en una línea

Inicio, Mis Clases, **Mi Asistencia**, **Comunicados** (lista y detalle), **Mensajes** y **Mi Perfil** comparten sidebar celeste, hero con métricas reales y datos desde la BD (no placeholders).

### Otras páginas ya alineadas (misma sesión / línea visual)

| Vista | Plantilla / CSS | Nota breve |
|-------|-----------------|------------|
| Mi Asistencia | `asistencia.html`, `asistencia.css` (`ma-`) | Filtros mes/materia/estado; métricas y registros reales |
| Mensajes | `mensajeria.html`, `mensajeria.css` (`mm-`) | Bandeja 3 columnas; colores por asignatura; envío desde detalle de clase |
| Mis Clases | `mis_clases.html`, `mis_clases.css` (`mc-` clases) | Ya documentado arriba (2026-05-26) |

---

## Mi Perfil + Comunicados + sidebar (detalle 2026-05-24)

> Esta parte **sí tocó backend** (perfil, comunicados, migración).

### Mi Perfil (`?pagina=perfil`)

| Qué | Detalle |
|-----|---------|
| Plantilla nueva | `estudiante/mi_perfil.html` + `estudiante/perfil_estudiante.css` (prefijo `mp-`) |
| Hero | Promedio, asistencia, total calificaciones y asignaturas **desde BD** (no números fijos) |
| Foto | El alumno puede subir/quitar foto (JPG/PNG/WebP, máx. 5 MB) |
| Editable | Email, teléfonos, dirección, contacto de emergencia, contraseña |
| Solo lectura | RUT, apoderado, curso, ciclo, datos académicos del colegio |
| Backend | Campo `foto_perfil` en `PerfilEstudiante` + migración `accounts.0012` |
| Servicios | `ProfileService`: `update_own_student_profile`, `upload_student_photo`, `change_own_student_password` (sin permiso admin) |

**Migración obligatoria en cada máquina:** `python manage.py migrate accounts`

**Media en desarrollo:** fotos en `/media/` (`core/urls.py` solo con `DEBUG=True`).

---

### Comunicados — lista (`/comunicados/`)

| Qué | Detalle |
|-----|---------|
| Plantilla | `comunicados/lista_comunicados_alumno.html` + `estudiante/comunicados.css` (`mc-`) |
| Métricas hero | Sin leer / Leídos / Urgentes / Total **reales** por alumno |
| Lista “Todos” | Muestra siempre los comunicados (antes, si todo estaba leído, solo salía el mensaje verde) |
| Chips | Siempre visible **Sin leer (N)** aunque N sea 0 |
| Secciones | Urgentes → Sin leer → Leídos (sin filtros activos) |
| Lectura | Al abrir el detalle se marca como leído |

---

### Comunicados — detalle (`/comunicados/<id>/`)

| Qué | Detalle |
|-----|---------|
| Problema corregido | Antes usaba `detalle_comunicado.html` del dashboard → fondo rojo y otra tipografía |
| Plantilla alumno | `comunicados/detalle_comunicado_alumno.html` — mismo layout que lista (sidebar + hero) |
| Contexto | Incluye `nombre_usuario` y menú (antes el sidebar quedaba sin nombre) |
| Navegación | Hero + breadcrumb `← Comunicados / Detalle` |
| Confirmación | Caja para confirmar asistencia si el comunicado lo pide |

Profesor/admin siguen con `comunicados/detalle_comunicado.html` (sin cambio de layout).

---

### Sidebar alumno (`_sidebar.html`)

- Muestra **nombre** aunque falte variable de contexto (`user.get_full_name` de respaldo).
- Muestra **foto de perfil** si existe (`foto_perfil` o `foto_perfil_url`).
- Estilos foto: `dashboard_alumno.css` → `.alumno-sidebar__avatar--photo`.

---

### Archivos clave (para revisar en Git)

**Frontend**
- `templates/estudiante/mi_perfil.html`
- `static/css/estudiante/perfil_estudiante.css`
- `templates/comunicados/lista_comunicados_alumno.html`
- `templates/comunicados/detalle_comunicado_alumno.html`
- `templates/comunicados/_comunicado_alumno_item.html`
- `static/css/estudiante/comunicados.css`
- `templates/estudiante/_sidebar.html`

**Backend**
- `backend/common/utils/permissions.py` → estudiante `perfil` → `mi_perfil.html`
- `backend/apps/core/services/dashboard_context_service.py` → contexto perfil alumno
- `backend/apps/accounts/services/profile_service.py` + `views/profile.py`
- `backend/apps/comunicados/views/comunicados.py` + `services/comunicados_service.py`
- `backend/apps/accounts/models.py` + migración `0012`

---

### Cómo probar (estudiante demo)

1. `python manage.py migrate` (si falta `0012`).
2. Login alumno (ej. `alumno1@colegio.cl`).
3. **Mi Perfil:** `dashboard/?pagina=perfil` — subir foto, guardar contacto.
4. **Comunicados:** menú Comunicados → ver lista en “Todos” → abrir uno → volver; contadores deben cuadrar.
5. **Ctrl+F5** si no se ven estilos (`comunicados.css?v=20260621`, `perfil_estudiante.css`).

---

### Coordinación con el equipo

- Posibles conflictos de merge: `dashboard_context_service.py`, `permissions.py`, `comunicados/views/comunicados.py`.
- La plantilla vieja `compartido/perfil.html` **sigue** para otros roles; no se borró.
- `estudiante/perfil.html` antigua sigue en el repo (no es la del dashboard actual).


