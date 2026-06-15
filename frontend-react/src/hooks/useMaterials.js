import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';

/**
 * Hook para obtener lista de materiales/recursos de clase
 * Cachea automaticamente y permite revalidación manual
 * 
 * @param {number} claseId - ID de la clase
 * @param {object} options - { skip, filters, onSuccess, onError }
 * @returns { materials, isLoading, isError, error, refetch }
 */
export function useMaterials(claseId, options = {}) {
  const {
    skip = false,
    filters = {},
    onSuccess = null,
    onError = null,
  } = options;

  const queryKey = ['materials', claseId, filters];

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      const params = new URLSearchParams({ clase_id: claseId, ...filters });
      return apiClient.get(`/api/v1/materiales/?${params}`);
    },
    enabled: !skip && !!claseId,
    staleTime: 1000 * 60 * 10, // 10 minutos (materiales cambian menos frecuentemente)
  });

  if (query.data && onSuccess) {
    onSuccess(query.data);
  }

  if (query.error && onError) {
    onError(query.error);
  }

  return {
    materials: query.data?.results || query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    isRefetching: query.isRefetching,
  };
}

/**
 * Hook para obtener detalle de un material
 * 
 * @param {number} materialId - ID del material
 * @param {object} options - { skip, onSuccess, onError }
 * @returns { material, isLoading, isError, error, refetch }
 */
export function useMaterial(materialId, options = {}) {
  const { skip = false, onSuccess = null, onError = null } = options;

  const query = useQuery({
    queryKey: ['materials', materialId],
    queryFn: () => apiClient.get(`/api/v1/materiales/${materialId}/`),
    enabled: !skip && !!materialId,
    staleTime: 1000 * 60 * 10,
  });

  if (query.data && onSuccess) {
    onSuccess(query.data);
  }

  if (query.error && onError) {
    onError(query.error);
  }

  return {
    material: query.data || null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Hook para descargar un material
 * Invalida cache de materiales después de descargar exitosamente
 * 
 * @param {object} options - { onSuccess, onError }
 * @returns { mutate, isPending, isError, error, data }
 */
export function useDownloadMaterial(options = {}) {
  const { onSuccess = null, onError = null } = options;

  const mutation = useMutation({
    mutationFn: (materialId) =>
      apiClient.get(`/api/v1/materiales/${materialId}/download/`, {
        responseType: 'blob',
      }),
    onSuccess: (data) => {
      if (onSuccess) onSuccess(data);
    },
    onError: (error) => {
      if (onError) onError(error);
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    data: mutation.data,
  };
}

/**
 * Hook para crear un nuevo material (profesor)
 * Invalida lista de materiales después de crear
 * 
 * @param {object} options - { onSuccess, onError }
 * @returns { mutate, isPending, isError, error }
 */
export function useCreateMaterial(options = {}) {
  const { onSuccess = null, onError = null } = options;
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload) =>
      apiClient.post('/api/v1/materiales/', payload, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }),
    onSuccess: (data, variables) => {
      // Revalidar lista de materiales de la clase
      queryClient.invalidateQueries({ queryKey: ['materials', variables.clase_id] });
      if (onSuccess) onSuccess(data);
    },
    onError: (error) => {
      if (onError) onError(error);
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
  };
}

/**
 * Hook para eliminar un material (profesor)
 * Invalida cache de materiales después de eliminar
 * 
 * @param {object} options - { onSuccess, onError }
 * @returns { mutate, isPending, isError, error }
 */
export function useDeleteMaterial(options = {}) {
  const { onSuccess = null, onError = null } = options;
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (materialId) =>
      apiClient.delete(`/api/v1/materiales/${materialId}/`),
    onSuccess: (data) => {
      // Revalidar todas las listas de materiales
      queryClient.invalidateQueries({ queryKey: ['materials'] });
      if (onSuccess) onSuccess(data);
    },
    onError: (error) => {
      if (onError) onError(error);
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
  };
}
