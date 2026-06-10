import { createContext, createElement, useContext, useEffect, useMemo, useState } from 'react';

import { apiClient } from '@/services/apiClient';

const TenantContext = createContext({
  tenant: null,
  baseTenant: null,
  isOverride: false,
  loading: false,
  error: null,
  setTenantOverride: () => {},
  clearTenantOverride: () => {},
});

function extractSubdomain(hostname) {
  if (!hostname) return null;
  const host = hostname.toLowerCase();
  if (host === 'localhost' || host === '127.0.0.1') return null;
  const parts = host.split('.');
  return parts.length > 2 ? parts[0] : null;
}

function buildTenantQuery({ hostname, rbdOverride }) {
  if (rbdOverride) {
    return `?rbd=${encodeURIComponent(rbdOverride)}`;
  }

  const subdomain = extractSubdomain(hostname);
  if (subdomain) {
    return `?slug=${encodeURIComponent(subdomain)}`;
  }

  const localTenantRbd = import.meta.env.VITE_TENANT_RBD;
  if (localTenantRbd) {
    return `?rbd=${encodeURIComponent(localTenantRbd)}`;
  }

  return '';
}

function applyTenantTheme(tenant) {
  const root = document.documentElement;
  if (!root) return;

  if (tenant?.color_primario) {
    root.style.setProperty('--brand', tenant.color_primario);
  } else {
    root.style.removeProperty('--brand');
  }
}

export function TenantProvider({ children }) {
  const [tenant, setTenant] = useState(null);
  const [baseTenant, setBaseTenant] = useState(null);
  const [overrideTenant, setOverrideTenant] = useState(null);
  const [overrideRbd, setOverrideRbd] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const setTenantOverride = (rbd) => {
    if (rbd) {
      setOverrideRbd(String(rbd));
    } else {
      setOverrideRbd('');
      setOverrideTenant(null);
    }
  };

  const clearTenantOverride = () => {
    setOverrideRbd('');
    setOverrideTenant(null);
  };

  async function loadTenant(query) {
    const payload = await apiClient.get(`/api/v1/tenant/info/${query}`);
    return payload;
  }

  useEffect(() => {
    let mounted = true;

    async function loadBaseTenant() {
      setLoading(true);
      setError(null);

      try {
        const query = buildTenantQuery({ hostname: window.location.hostname });
        const payload = await loadTenant(query);
        if (mounted) {
          setBaseTenant(payload);
        }
      } catch (err) {
        if (mounted) {
          setBaseTenant(null);
          setError(err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadBaseTenant();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    async function loadOverrideTenant() {
      if (!overrideRbd) {
        setOverrideTenant(null);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const query = buildTenantQuery({ hostname: window.location.hostname, rbdOverride: overrideRbd });
        const payload = await loadTenant(query);
        if (mounted) {
          setOverrideTenant(payload);
        }
      } catch (err) {
        if (mounted) {
          setOverrideTenant(null);
          setError(err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadOverrideTenant();
    return () => {
      mounted = false;
    };
  }, [overrideRbd]);

  useEffect(() => {
    const effectiveTenant = overrideTenant || baseTenant;
    setTenant(effectiveTenant);
    applyTenantTheme(effectiveTenant);
  }, [baseTenant, overrideTenant]);

  const value = useMemo(
    () => ({
      tenant,
      baseTenant,
      isOverride: Boolean(overrideTenant),
      loading,
      error,
      setTenantOverride,
      clearTenantOverride,
    }),
    [tenant, baseTenant, overrideTenant, loading, error]
  );

  return createElement(TenantContext.Provider, { value }, children);
}

export function useTenant() {
  return useContext(TenantContext);
}
