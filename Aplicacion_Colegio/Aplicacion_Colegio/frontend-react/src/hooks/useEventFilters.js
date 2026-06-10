import { useState, useMemo } from 'react';

/**
 * useEventFilters - Manage filter state and query building for calendar events
 * 
 * Centralizes filter state and query string building to avoid duplication in pages.
 * 
 * @param {Object} config
 * @param {Object} config.initialFilters - Default filter values: { tipo: '', mes: '', anio: '', desde: '', hasta: '' }
 * 
 * @returns {Object} { filters, setFilters, updateFilter, clearFilters, activeFilters, buildQuery }
 */
export function useEventFilters(initialFilters = {}) {
  const defaults = {
    tipo: '',
    mes: '',
    anio: '',
    desde: '',
    hasta: '',
    ...initialFilters,
  };

  const [filters, setFilters] = useState(defaults);

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters(defaults);
  };

  const activeFilters = useMemo(
    () =>
      Object.entries(filters)
        .filter(([_, v]) => v !== '' && v !== null)
        .reduce((acc, [k, v]) => ({ ...acc, [k]: v }), {}),
    [filters]
  );

  const buildQuery = () => {
    const params = new URLSearchParams();
    Object.entries(activeFilters).forEach(([key, value]) => {
      params.append(key, value);
    });
    return params.toString();
  };

  return {
    filters,
    setFilters,
    updateFilter,
    clearFilters,
    activeFilters,
    buildQuery,
  };
}
