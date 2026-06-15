import { useEffect } from 'react';

/**
 * usePageMeta
 *
 * Hook para actualizar dinámicamente metatags y title.
 * Útil para SEO, social sharing y accesibilidad.
 *
 * Uso:
 * usePageMeta({
 *   title: 'Mis Estudiantes',
 *   description: 'Gestiona tus estudiantes de manera fácil',
 *   og: {
 *     type: 'website',
 *     image: 'https://...',
 *   }
 * });
 */
export function usePageMeta({
  title = 'Colegio SaaS - Plataforma de Gestión Escolar',
  description = 'Plataforma de gestión escolar SaaS - administra estudiantes, notas, asistencia y más.',
  og = {},
  canonical = null,
} = {}) {
  useEffect(() => {
    // Update title
    const originalTitle = document.title;
    document.title = title;

    // Update meta description
    let descTag = document.querySelector('meta[name="description"]');
    if (!descTag) {
      descTag = document.createElement('meta');
      descTag.setAttribute('name', 'description');
      document.head.appendChild(descTag);
    }
    descTag.setAttribute('content', description);

    // Update Open Graph tags
    const ogTags = {
      'og:title': og.title || title,
      'og:description': og.description || description,
      'og:type': og.type || 'website',
      ...(og.image && { 'og:image': og.image }),
      ...(og.url && { 'og:url': og.url }),
    };

    Object.entries(ogTags).forEach(([property, content]) => {
      let tag = document.querySelector(`meta[property="${property}"]`);
      if (!tag) {
        tag = document.createElement('meta');
        tag.setAttribute('property', property);
        document.head.appendChild(tag);
      }
      tag.setAttribute('content', content);
    });

    // Update canonical URL if provided
    if (canonical) {
      let canonicalTag = document.querySelector('link[rel="canonical"]');
      if (!canonicalTag) {
        canonicalTag = document.createElement('link');
        canonicalTag.setAttribute('rel', 'canonical');
        document.head.appendChild(canonicalTag);
      }
      canonicalTag.setAttribute('href', canonical);
    }

    // Cleanup on unmount: restore original title
    return () => {
      document.title = originalTitle;
    };
  }, [title, description, og, canonical]);
}

/**
 * setPageMeta (helper for imperative usage)
 *
 * Alternative to usePageMeta if you need to set meta tags imperatively.
 * Useful in loaders or non-component contexts.
 *
 * Uso:
 * setPageMeta({
 *   title: 'Página',
 *   description: 'Desc...',
 * });
 */
export function setPageMeta({
  title = 'Colegio SaaS - Plataforma de Gestión Escolar',
  description = 'Plataforma de gestión escolar SaaS - administra estudiantes, notas, asistencia y más.',
  og = {},
  canonical = null,
} = {}) {
  // Update title
  document.title = title;

  // Update meta description
  let descTag = document.querySelector('meta[name="description"]');
  if (!descTag) {
    descTag = document.createElement('meta');
    descTag.setAttribute('name', 'description');
    document.head.appendChild(descTag);
  }
  descTag.setAttribute('content', description);

  // Update Open Graph tags
  const ogTags = {
    'og:title': og.title || title,
    'og:description': og.description || description,
    'og:type': og.type || 'website',
    ...(og.image && { 'og:image': og.image }),
    ...(og.url && { 'og:url': og.url }),
  };

  Object.entries(ogTags).forEach(([property, content]) => {
    let tag = document.querySelector(`meta[property="${property}"]`);
    if (!tag) {
      tag = document.createElement('meta');
      tag.setAttribute('property', property);
      document.head.appendChild(tag);
    }
    tag.setAttribute('content', content);
  });

  // Update canonical URL if provided
  if (canonical) {
    let canonicalTag = document.querySelector('link[rel="canonical"]');
    if (!canonicalTag) {
      canonicalTag = document.createElement('link');
      canonicalTag.setAttribute('rel', 'canonical');
      document.head.appendChild(canonicalTag);
    }
    canonicalTag.setAttribute('href', canonical);
  }
}

