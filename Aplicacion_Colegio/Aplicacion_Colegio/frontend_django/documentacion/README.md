# Documentación del frontend Django

Carpeta para registrar cambios del portal **server-rendered** (`frontend_django`), en formato breve y legible, similar a `Documentacion/Frontend/` del repositorio.

## Qué va aquí

| Tipo | Archivo / patrón | Contenido |
|------|------------------|-----------|
| Cambios solo de UI (HTML/CSS) | `CAMBIOS_VISUALES.md` y futuros `CAMBIOS_VISUALES_YYYY-MM-DD.md` si hace falta | Paleta, plantillas, assets; sin lógica Python |
| Otros temas visuales | Nuevos `.md` con nombre claro | Por ejemplo: accesibilidad, responsive, PWA del template |

## Qué no va aquí

- Lógica de negocio, views, urls, modelos → `Documentacion/Backend/`
- Frontend React → `Documentacion/Frontend/React_*.md`
- Reglas globales del proyecto → `Documentacion/REGLAS_PROYECTO.md`

## Alcance técnico habitual

Solo se documentan cambios bajo:

- `templates/`
- `static/css/`
- `static/img/` (referencias en plantillas)

No incluir cambios en `frontend-react/` ni en `backend/`.
