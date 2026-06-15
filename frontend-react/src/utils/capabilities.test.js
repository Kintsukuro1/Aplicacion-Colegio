import { describe, expect, it } from 'vitest';

import {
  canAccessRoute,
  getUserRole,
  hasAllCapabilities,
  hasAnyCapability,
  hasAllowedRole,
  hasCapability,
  isSystemAdmin,
  normalizeRole,
} from './capabilities';

describe('capabilities helpers', () => {
  const me = {
    capabilities: ['STUDENT_VIEW', 'GRADE_VIEW', 'CLASS_VIEW_ATTENDANCE'],
  };

  it('hasCapability returns true when capability exists', () => {
    expect(hasCapability(me, 'STUDENT_VIEW')).toBe(true);
  });

  it('hasCapability returns false without capabilities array', () => {
    expect(hasCapability({}, 'STUDENT_VIEW')).toBe(false);
    expect(hasCapability(null, 'STUDENT_VIEW')).toBe(false);
  });

  it('hasAnyCapability works with mixed capability list', () => {
    expect(hasAnyCapability(me, ['GRADE_EDIT', 'GRADE_VIEW'])).toBe(true);
    expect(hasAnyCapability(me, ['GRADE_EDIT', 'GRADE_DELETE'])).toBe(false);
  });

  it('hasAllCapabilities validates full set', () => {
    expect(hasAllCapabilities(me, ['STUDENT_VIEW', 'GRADE_VIEW'])).toBe(true);
    expect(hasAllCapabilities(me, ['STUDENT_VIEW', 'GRADE_EDIT'])).toBe(false);
  });

  it('isSystemAdmin detects override capability', () => {
    expect(isSystemAdmin({ capabilities: ['SYSTEM_ADMIN'] })).toBe(true);
    expect(isSystemAdmin(me)).toBe(false);
  });

  it('normalizes display role names to route role keys', () => {
    expect(normalizeRole('Estudiante')).toBe('estudiante');
    expect(normalizeRole('Coordinador académico')).toBe('coordinador_academico');
    expect(getUserRole({ user: { role: 'Administrador escolar' } })).toBe('admin_escolar');
    expect(hasAllowedRole({ role: 'Estudiante' }, ['estudiante', 'profesor'])).toBe(true);
  });
});

describe('canAccessRoute', () => {
  const baseUser = { capabilities: ['STUDENT_VIEW', 'GRADE_VIEW'] };

  it('denies when user is missing', () => {
    expect(canAccessRoute(null, { anyOf: ['STUDENT_VIEW'] })).toBe(false);
  });

  it('allows route with anyOf when one capability exists', () => {
    expect(canAccessRoute(baseUser, { anyOf: ['GRADE_EDIT', 'GRADE_VIEW'] })).toBe(true);
  });

  it('denies route with anyOf when no capability exists', () => {
    expect(canAccessRoute(baseUser, { anyOf: ['GRADE_EDIT', 'GRADE_DELETE'] })).toBe(false);
  });

  it('allows route with allOf only when all capabilities exist', () => {
    expect(canAccessRoute(baseUser, { allOf: ['STUDENT_VIEW', 'GRADE_VIEW'] })).toBe(true);
    expect(canAccessRoute(baseUser, { allOf: ['STUDENT_VIEW', 'GRADE_EDIT'] })).toBe(false);
  });

  it('enforces allowedRoles before capabilities', () => {
    const student = { role: 'Estudiante', capabilities: ['CLASS_VIEW'] };
    const teacherRoute = { allowedRoles: ['profesor'], anyOf: ['CLASS_VIEW'] };
    expect(canAccessRoute(student, teacherRoute)).toBe(false);
  });

  it('requires allOf and anyOf when both are declared', () => {
    const user = { capabilities: ['GRADE_VIEW'] };
    const route = { allOf: ['DASHBOARD_VIEW_SCHOOL'], anyOf: ['GRADE_VIEW'] };
    expect(canAccessRoute(user, route)).toBe(false);
  });

  it('gives SYSTEM_ADMIN full route access', () => {
    const admin = { capabilities: ['SYSTEM_ADMIN'] };
    expect(canAccessRoute(admin, { anyOf: ['NON_EXISTENT_CAP'] })).toBe(true);
    expect(canAccessRoute(admin, { allOf: ['ALSO_MISSING'] })).toBe(true);
  });
});
