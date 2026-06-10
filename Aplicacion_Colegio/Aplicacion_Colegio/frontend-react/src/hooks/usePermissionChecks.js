import { useMemo } from 'react';
import { useAuthStore } from '@/stores/useAuthStore';
import { hasAnyCapability } from '@/utils/capabilities';

/**
 * usePermissionChecks - Centralized permission validation for CRUD operations
 * 
 * Returns memoized permission checks to avoid recalculating on every render.
 * Automatically retrieves user from AuthStore.
 * 
 * @param {Object} config
 * @param {string[]} config.viewCapabilities - Capabilities required to view (e.g., ['LIST_STUDENTS'])
 * @param {string[]} config.createCapabilities - Capabilities required to create
 * @param {string[]} config.updateCapabilities - Capabilities required to update
 * @param {string[]} config.deleteCapabilities - Capabilities required to delete
 * 
 * @returns {Object} { canView, canCreate, canUpdate, canDelete, userCapabilities }
 */
export function usePermissionChecks({
  viewCapabilities = [],
  createCapabilities = [],
  updateCapabilities = [],
  deleteCapabilities = [],
} = {}) {
  const me = useAuthStore((state) => state.user);

  const permissions = useMemo(() => {
    return {
      canView: hasAnyCapability(me, viewCapabilities),
      canCreate: hasAnyCapability(me, createCapabilities),
      canUpdate: hasAnyCapability(me, updateCapabilities),
      canDelete: hasAnyCapability(me, deleteCapabilities),
    };
  }, [me, viewCapabilities, createCapabilities, updateCapabilities, deleteCapabilities]);

  return permissions;
}
