import { useState, useCallback, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';

const EMPTY_ITEMS = [];

/**
 * Hook para manejar paginación con un endpoint API usando TanStack Query
 *
 * @param {string} baseUrl - URL base endpoint (ej: '/api/v1/estudiantes/')
 * @param {object} options - Opciones adicionales
 *   - initialLimit: number - items por página (default: 10)
 *   - onSuccess: (data, total) => void - callback con datos y total
 *   - onError: (error) => void - callback de error
 *   - params: object - parámetros query adicionales
 *   - pageMode: boolean - si `true` usa `page` en la query en vez de `offset`/`limit`
 *   - skip: boolean - si `true` no ejecuta el query
 *
 * @returns {object} {
 *   items, loading, error,
 *   pagination: { currentPage, totalPages, offset, limit, total },
 *   goToPage, nextPage, prevPage, setLimit, refetch
 * }
 */
export function usePagination(baseUrl, options = {}) {
  const {
    initialLimit = 10,
    onSuccess = null,
    onError = null,
    params = {},
    pageMode = false,
    skip = false,
  } = options;

  const [offset, setOffset] = useState(0);
  const [limit, setLimitState] = useState(initialLimit);

  const currentPage = Math.floor(offset / limit) + 1;

  // Memoize queryKey to avoid creating new observers on every render
  const queryKey = useMemo(() => {
    const pageNumber = pageMode ? Math.floor(offset / limit) + 1 : null;
    const baseParams = pageMode ? { page: pageNumber, ...params } : { offset, limit, ...params };
    const sortedParams = Object.keys(baseParams)
      .sort()
      .reduce((acc, key) => {
        acc[key] = baseParams[key];
        return acc;
      }, {});
    return [baseUrl, JSON.stringify(sortedParams)];
  }, [baseUrl, offset, limit, params, pageMode]);

  const { data, isFetching: loading, error: queryError, refetch } = useQuery({
    queryKey,
    queryFn: async () => {
      const pageNumber = pageMode ? Math.floor(offset / limit) + 1 : null;
      const baseParams = pageMode ? { page: pageNumber, ...params } : { offset, limit, ...params };
      const queryString = new URLSearchParams(baseParams).toString();
      const url = `${baseUrl}?${queryString}`;
      return await apiClient.get(url);
    },
    enabled: !skip,
  });

  const error = queryError?.message || queryError;
  const items = data?.results || data?.data || EMPTY_ITEMS;
  const total = data?.count || data?.total || 0;
  const totalPages = Math.ceil(total / limit) || 0;

  useEffect(() => {
    if (data && onSuccess) {
      const successItems = data?.results || data?.data || [];
      const successTotal = data?.count || data?.total || 0;
      onSuccess(successItems, successTotal);
    }
  }, [data, onSuccess]);

  useEffect(() => {
    if (queryError && onError) {
      onError(queryError);
    }
  }, [queryError, onError]);

  const goToPage = useCallback((pageNum) => {
    const numericPage = Number(pageNum);
    const normalized = Number.isFinite(numericPage) && numericPage > 0 ? (numericPage - 1) * limit : 0;
    setOffset(normalized);
  }, [limit]);

  const nextPage = useCallback(() => {
    if (currentPage < totalPages) {
      goToPage(currentPage + 1);
    }
  }, [currentPage, totalPages, goToPage]);

  const prevPage = useCallback(() => {
    if (currentPage > 0) {
      goToPage(currentPage - 1);
    }
  }, [currentPage, goToPage]);

  const setLimitAndReset = useCallback((newLimit) => {
    setLimitState(newLimit);
    setOffset(0);
  }, []);

  return {
    items,
    loading,
    error,
    pagination: {
      currentPage,
      totalPages,
      offset,
      limit,
      total,
    },
    goToPage,
    nextPage,
    prevPage,
    setLimit: setLimitAndReset,
    refetch,
  };
}
