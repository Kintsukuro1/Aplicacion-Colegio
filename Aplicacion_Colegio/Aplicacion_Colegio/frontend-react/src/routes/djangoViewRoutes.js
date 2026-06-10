import { normalizeRole } from '../utils/capabilities';

export const DJANGO_DASHBOARD_PAGE_ROUTES = {
  profesor: {
    inicio: '/dashboard',
    mis_clases: '/profesor/clases',
    asistencia: '/profesor/asistencias',
    notas: '/profesor/calificaciones',
    libro_notas: '/profesor/calificaciones',
    calendario_eventos: '/calendario/eventos',
    solicitud_reuniones: '/reuniones/solicitudes',
    perfil: '/dashboard',
  },
  estudiante: {
    inicio: '/estudiante/panel?tab=perfil',
    perfil: '/estudiante/panel?tab=perfil',
    mis_clases: '/estudiante/panel?tab=clases',
    mi_horario: '/estudiante/panel?tab=clases',
    mis_evaluaciones: '/estudiante/panel?tab=notas',
    mis_notas: '/estudiante/panel?tab=notas',
    asistencia: '/estudiante/panel?tab=asistencia',
    mi_asistencia: '/estudiante/panel?tab=asistencia',
    mis_tareas: '/estudiante/panel?tab=tareas',
    calendario_tareas: '/estudiante/panel?tab=calendario_tareas',
    comunicados: '/estudiante/panel?tab=comunicados',
    mensajes: '/estudiante/panel?tab=mensajes',
    mis_anotaciones: '/estudiante/panel?tab=historial',
    mis_certificados: '/estudiante/panel?tab=certificados',
    estado_cuenta: '/estudiante/panel?tab=estado_cuenta',
    mis_pagos: '/estudiante/panel?tab=mis_pagos',
    dashboard_graficos: '/estudiante/panel?tab=dashboard_graficos',
  },
  apoderado: {
    inicio: '/apoderado/panel?tab=resumen',
    perfil: '/apoderado/panel?tab=perfil',
    mis_pupilos: '/apoderado/panel?tab=pupilos',
    notas: '/apoderado/panel?tab=notas',
    asistencia: '/apoderado/panel?tab=asistencia',
    mis_certificados: '/apoderado/panel?tab=certificados',
    justificativos: '/apoderado/panel?tab=justificativos',
    firmas_pendientes: '/apoderado/panel?tab=firmas',
    calendario_pupilo: '/apoderado/panel?tab=calendario',
    admision_matricula: '/apoderado/panel?tab=admision',
    comunicados: '/apoderado/panel?tab=comunicados',
    mensajes: '/apoderado/panel?tab=mensajes',
    estado_cuenta: '/apoderado/panel?tab=estado_cuenta',
    mis_pagos: '/apoderado/panel?tab=mis_pagos',
  },
};

export function getReactRouteForDjangoPage(role, pageName) {
  const normalizedRole = normalizeRole(role);
  const normalizedPage = String(pageName || '').trim();
  return DJANGO_DASHBOARD_PAGE_ROUTES[normalizedRole]?.[normalizedPage] || null;
}

export function buildReactRouteForDjangoPage(role, pageName, currentSearchParams = new URLSearchParams()) {
  const route = getReactRouteForDjangoPage(role, pageName);
  if (!route) {
    return null;
  }

  const [pathname, queryString = ''] = route.split('?');
  const targetParams = new URLSearchParams(queryString);

  currentSearchParams.forEach((value, key) => {
    if (key !== 'pagina' && !targetParams.has(key)) {
      targetParams.append(key, value);
    }
  });

  const nextQueryString = targetParams.toString();
  return nextQueryString ? `${pathname}?${nextQueryString}` : pathname;
}
