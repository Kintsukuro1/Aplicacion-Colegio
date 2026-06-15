export function hasCapability(me, capability) {
  if (!me || !Array.isArray(me.capabilities)) {
    return false;
  }
  return me.capabilities.includes(capability);
}

export function hasAnyCapability(me, capabilities = []) {
  return capabilities.some((cap) => hasCapability(me, cap));
}

export function hasAllCapabilities(me, capabilities = []) {
  return capabilities.every((cap) => hasCapability(me, cap));
}

export function isSystemAdmin(me) {
  return hasCapability(me, 'SYSTEM_ADMIN');
}

export function normalizeRole(role) {
  const normalized = String(role || '')
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');

  const aliases = {
    alumno: 'estudiante',
    pupilo: 'estudiante',
    administrador: 'admin',
    administrador_escolar: 'admin_escolar',
    administrador_general: 'admin_general',
    admin_escolar: 'admin_escolar',
    admin_general: 'admin_general',
    soporte_tecnico: 'soporte_tecnico_escolar',
    psicologo: 'psicologo_orientador',
    orientador: 'psicologo_orientador',
    inspector: 'inspector_convivencia',
    bibliotecario: 'bibliotecario_digital',
  };

  return aliases[normalized] || normalized;
}

export function getUserRole(me) {
  return normalizeRole(me?.role || me?.user?.role);
}

export function hasAllowedRole(me, allowedRoles = []) {
  if (!allowedRoles.length) {
    return true;
  }

  const currentRole = getUserRole(me);
  return allowedRoles.map(normalizeRole).includes(currentRole);
}

export function canAccessRoute(me, route) {
  if (!me) {
    return false;
  }

  if (route.allowedRoles && !hasAllowedRole(me, route.allowedRoles)) {
    return false;
  }

  if (isSystemAdmin(me)) {
    return true;
  }

  if (route.allOf && route.allOf.length > 0 && !hasAllCapabilities(me, route.allOf)) {
    return false;
  }

  if (route.anyOf && route.anyOf.length > 0) {
    return hasAnyCapability(me, route.anyOf);
  }

  return true;
}
