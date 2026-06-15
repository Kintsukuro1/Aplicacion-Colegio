import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';

/**
 * Hook para obtener lista de tareas del estudiante
 * Cachea automaticamente y permite revalidación manual
 * 
 * @param {object} options - { skip, filters, onSuccess, onError }
 * @returns { tasks, isLoading, isError, error, refetch }
 */
export function useTasks(options = {}) {
  const {
    skip = false,
    filters = {},
    onSuccess = null,
    onError = null,
  } = options;

  const queryKey = ['tasks', filters];

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      const params = new URLSearchParams(filters);
      return apiClient.get(`/api/v1/estudiante/tareas/${params ? '?' + params : ''}`);
    },
    enabled: !skip,
    staleTime: 1000 * 60 * 5, // 5 minutos
  });

  // Ejecutar callback cuando tenemos datos
  if (query.data && onSuccess) {
    onSuccess(query.data);
  }

  // Ejecutar callback en error
  if (query.error && onError) {
    onError(query.error);
  }

  return {
    tasks: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    isRefetching: query.isRefetching,
  };
}

/**
 * Hook para obtener detalle de una tarea
 * 
 * @param {number} tareaId - ID de la tarea
 * @param {object} options - { skip, onSuccess, onError }
 * @returns { task, isLoading, isError, error, refetch }
 */
export function useTask(tareaId, options = {}) {
  const { skip = false, onSuccess = null, onError = null } = options;

  const query = useQuery({
    queryKey: ['tasks', tareaId],
    queryFn: () => apiClient.get(`/api/v1/estudiante/tarea/${tareaId}/`),
    enabled: !skip && !!tareaId,
    staleTime: 1000 * 60 * 5,
  });

  if (query.data && onSuccess) {
    onSuccess(query.data);
  }

  if (query.error && onError) {
    onError(query.error);
  }

  return {
    task: query.data || null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Hook para entregar una tarea
 * Invalida automaticamente el cache de tareas después de una entrega exitosa
 * 
 * @param {object} options - { onSuccess, onError }
 * @returns { mutate, isPending, isError, error, data }
 */
export function useSubmitTask(options = {}) {
  const { onSuccess = null, onError = null } = options;
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload) =>
      apiClient.post('/api/v1/estudiante/tareas/entregar/', payload),
    onSuccess: (data) => {
      // Revalidar lista de tareas y detalle si existe en caché
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
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
 * Hook para actualizar estado de tarea
 * Useful para cambiar estado (pendiente, entregada, corregida, vencida)
 * 
 * @param {object} options - { onSuccess, onError }
 * @returns { mutate, isPending, isError, error }
 */
export function useUpdateTaskStatus(options = {}) {
  const { onSuccess = null, onError = null } = options;
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({ tareaId, estado }) =>
      apiClient.patch(`/api/v1/estudiante/tarea/${tareaId}/estado/`, { estado }),
    onSuccess: (data, variables) => {
      // Revalidar tarea específica y lista
      queryClient.invalidateQueries({ queryKey: ['tasks', variables.tareaId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
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
