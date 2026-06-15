# Shared Assets — Imágenes del Proyecto

Carpeta compartida de recursos visuales accesible tanto por **Django** (vía `STATICFILES_DIRS`) como por **React/Vite** (vía proxy de desarrollo y build de producción).

## Estructura

```
shared_assets/
├── images/
│   ├── branding/      # Logos, favicon, iconos institucionales
│   ├── ui/            # Fondos, banners, elementos decorativos de la UI
│   └── content/       # Imágenes de contenido educativo reutilizable
└── README.md
```

## Uso

### Desde Django Templates
```html
{% load static %}
<img src="{% static 'images/branding/favicon.ico' %}" alt="Logo">
```

### Desde React (desarrollo)
```jsx
// Las imágenes se sirven vía proxy a Django en desarrollo
<img src="/shared/images/branding/favicon.ico" alt="Logo" />
```

### Desde React (producción)
En producción, las imágenes se sirven directamente desde el backend Django
a través de `collectstatic`, por lo que el path `/static/images/...` funciona.

## Convenciones

- **Formatos preferidos**: `.webp` para web, `.svg` para iconos/logos, `.png` para transparencia
- **Tamaño máximo recomendado**: 500 KB por imagen
- **Nomenclatura**: `kebab-case` (ej: `logo-colegio-dark.webp`)
- **No subir**: imágenes temporales, capturas de pantalla de debug, archivos PSD/AI
