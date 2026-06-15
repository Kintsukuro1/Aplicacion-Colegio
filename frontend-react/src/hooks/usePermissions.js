import { useMemo } from 'react';

import { hasAllCapabilities, hasAnyCapability, hasCapability, isSystemAdmin } from '@/utils/capabilities';

export function usePermissions(me) {
  return useMemo(() => {
    const can = (capability) => hasCapability(me, capability);
    const canAny = (capabilities = []) => hasAnyCapability(me, capabilities);
    const canAll = (capabilities = []) => hasAllCapabilities(me, capabilities);
    const isAdmin = isSystemAdmin(me) || hasCapability(me, 'SYSTEM_CONFIGURE');

    return {
      can,
      canAny,
      canAll,
      isAdmin,
      isSystemAdmin: isSystemAdmin(me),
      hasRole: (roleName) => String(me?.role || '').toLowerCase() === String(roleName || '').toLowerCase(),
    };
  }, [me]);
}