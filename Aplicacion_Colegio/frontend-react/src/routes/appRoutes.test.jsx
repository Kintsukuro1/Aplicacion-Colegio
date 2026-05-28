import { describe, expect, it } from 'vitest';

import { canAccessRoute } from '../utils/capabilities';
import { APP_ROUTES } from './appRoutes';

const DEFAULT_CAPABILITIES_BY_ROLE = {
  profesor: [
    'DASHBOARD_VIEW_SELF',
    'STUDENT_VIEW',
    'STUDENT_VIEW_ACADEMIC',
    'CLASS_VIEW',
    'CLASS_TAKE_ATTENDANCE',
    'CLASS_VIEW_ATTENDANCE',
    'LIBRO_CLASE_VIEW',
    'LIBRO_CLASE_EDIT',
    'LIBRO_CLASE_FIRMAR',
    'GRADE_VIEW',
    'GRADE_CREATE',
    'GRADE_EDIT',
    'ANNOUNCEMENT_VIEW',
    'ANNOUNCEMENT_CREATE',
    'ANNOUNCEMENT_EDIT',
    'REPORT_VIEW_BASIC',
  ],
  estudiante: [
    'DASHBOARD_VIEW_SELF',
    'CLASS_VIEW',
    'CLASS_VIEW_ATTENDANCE',
    'GRADE_VIEW',
    'ANNOUNCEMENT_VIEW',
    'PORTAL_ESTUDIANTE',
  ],
  apoderado: [
    'DASHBOARD_VIEW_SELF',
    'STUDENT_VIEW',
    'STUDENT_VIEW_ACADEMIC',
    'CLASS_VIEW_ATTENDANCE',
    'GRADE_VIEW',
    'ANNOUNCEMENT_VIEW',
    'FINANCE_VIEW',
    'PORTAL_APODERADO',
  ],
  inspector_convivencia: [
    'DASHBOARD_VIEW_SCHOOL',
    'STUDENT_VIEW',
    'STUDENT_VIEW_DISCIPLINE',
    'CLASS_VIEW',
    'CLASS_TAKE_ATTENDANCE',
    'CLASS_VIEW_ATTENDANCE',
    'REPORT_VIEW_BASIC',
    'ANNOUNCEMENT_VIEW',
    'DISCIPLINE_VIEW',
    'DISCIPLINE_CREATE',
    'DISCIPLINE_EDIT',
    'JUSTIFICATION_VIEW',
    'JUSTIFICATION_APPROVE',
  ],
};

function visiblePathsFor(role) {
  const me = { role, capabilities: DEFAULT_CAPABILITIES_BY_ROLE[role] || [] };
  return APP_ROUTES.filter((route) => canAccessRoute(me, route)).map((route) => route.path);
}

describe('APP_ROUTES', () => {
  it('exposes a stable route contract', () => {
    expect(APP_ROUTES.length).toBeGreaterThan(0);

    const paths = new Set();

    APP_ROUTES.forEach((route) => {
      expect(route.path).toBeTruthy();
      expect(route.to).toBeTruthy();
      expect(route.label).toBeTruthy();
      expect(route.component).toBeTruthy();
      expect(paths.has(route.path)).toBe(false);
      paths.add(route.path);
    });
  });

  it('keeps role-owned modules restricted to their owning roles', () => {
    const ownedModules = {
      profesor: ['profesor'],
      estudiante: ['estudiante'],
      apoderado: ['apoderado'],
      inspector_convivencia: ['inspector-convivencia'],
    };

    Object.keys(DEFAULT_CAPABILITIES_BY_ROLE).forEach((role) => {
      const paths = visiblePathsFor(role);
      const forbiddenModules = Object.values(ownedModules)
        .flat()
        .filter((module) => !ownedModules[role]?.includes(module));

      forbiddenModules.forEach((module) => {
        expect(paths.some((path) => path.startsWith(`${module}/`))).toBe(false);
      });
    });
  });

  it('allows each core role to see its primary React entry point', () => {
    expect(visiblePathsFor('profesor')).toContain('profesor/calificaciones');
    expect(visiblePathsFor('estudiante')).toContain('estudiante/panel');
    expect(visiblePathsFor('apoderado')).toContain('apoderado/panel');
    expect(visiblePathsFor('inspector_convivencia')).toContain('inspector-convivencia/panel');
  });
});
