import { useState, useEffect } from 'react';
import { apiClient } from '@/services/apiClient';

/**
 * Hook para obtener datos de un endpoint API
 * Maneja automáticamente loading, error y data
 *
 * @param {string} url - URL endpoint (ej: '/api/v1/me/')
 * @param {object} options - Opciones adicionales
 *   - skip: boolean - saltar la llamada inicial (default: false)
 *   - onSuccess: (data) => void - callback cuando se obtienen datos
 *   - onError: (error) => void - callback cuando hay error
 *   - dependencies: array - array de dependencias adicionales
 *
 * @returns {object} { data, loading, error, refetch }
 */
export function useFetch(url, options = {}) {
  const {
    skip = false,
    onSuccess = null,
    onError = null,
    dependencies = [],
  } = options;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(!skip);
  const [error, setError] = useState(null);

  const fetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.get(url);
      setData(result);
      if (onSuccess) onSuccess(result);
    } catch (err) {
      const errorMsg = err?.message || 'Error fetching data';
      setError(errorMsg);
      if (onError) onError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (skip || !url) return;
    fetch();
  }, [url, skip, ...dependencies]);

  return {
    data,
    loading,
    error,
    refetch: fetch,
  };
}
