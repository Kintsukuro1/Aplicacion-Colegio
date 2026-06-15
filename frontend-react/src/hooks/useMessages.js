import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/apiClient';

/**
 * Hook para obtener bandeja de mensajes del usuario
 * Soporta paginación y filtros
 * 
 * @param {object} options - { skip, filters, page, limit, onSuccess, onError }
 * @returns { messages, isLoading, isError, error, refetch, pagination }
 */
export function useMessages(options = {}) {
  const {
    skip = false,
    filters = {},
    page = 1,
    limit = 20,
    onSuccess = null,
    onError = null,
  } = options;

  const queryKey = ['messages', { page, limit, ...filters }];

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      const params = new URLSearchParams({
        page,
        limit,
        ...filters,
      });
      return apiClient.get(`/api/v1/mensajeria/?${params}`);
    },
    enabled: !skip,
    staleTime: 1000 * 60 * 2, // 2 minutos (mensajes actualizan con frecuencia)
  });

  if (query.data && onSuccess) {
    onSuccess(query.data);
  }

  if (query.error && onError) {
    onError(query.error);
  }

  return {
    messages: query.data?.results || query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    isRefetching: query.isRefetching,
    pagination: {
      count: query.data?.count || 0,
      next: query.data?.next || null,
      previous: query.data?.previous || null,
      total_pages: Math.ceil((query.data?.count || 0) / limit),
      current_page: page,
    },
  };
}

/**
 * Hook para obtener una conversación específica
 * 
 * @param {number} conversationId - ID de la conversación
 * @param {object} options - { skip, onSuccess, onError }
 * @returns { conversation, isLoading, isError, error, refetch }
 */
export function useConversation(conversationId, options = {}) {
  const { skip = false, onSuccess = null, onError = null } = options;

  const query = useQuery({
    queryKey: ['messages', 'conversation', conversationId],
    queryFn: () =>
      apiClient.get(`/api/v1/mensajeria/conversacion/${conversationId}/`),
    enabled: !skip && !!conversationId,
    staleTime: 1000 * 60 * 1, // 1 minuto (conversaciones activas actualizan frecuentemente)
  });

  if (query.data && onSuccess) {
    onSuccess(query.data);
  }

  if (query.error && onError) {
    onError(query.error);
  }

  return {
    conversation: query.data || null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Hook para enviar un mensaje
 * Invalida cache de conversación y bandeja de mensajes
 * 
 * @param {object} options - { onSuccess, onError }
 * @returns { mutate, isPending, isError, error, data }
 */
export function useSendMessage(options = {}) {
  const { onSuccess = null, onError = null } = options;
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload) =>
      apiClient.post('/api/v1/mensajeria/enviar/', payload),
    onSuccess: (data, variables) => {
      // Revalidar conversación específica
      if (variables.conversation_id) {
        queryClient.invalidateQueries({
          queryKey: ['messages', 'conversation', variables.conversation_id],
        });
      }
      // Revalidar lista de mensajes
      queryClient.invalidateQueries({ queryKey: ['messages'] });
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
 * Hook para marcar mensajes como leídos
 * Invalida cache de conversación
 * 
 * @param {object} options - { onSuccess, onError }
 * @returns { mutate, isPending, isError, error }
 */
export function useMarkMessagesAsRead(options = {}) {
  const { onSuccess = null, onError = null } = options;
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload) =>
      apiClient.post('/api/v1/mensajeria/marcar-leidos/', payload),
    onSuccess: (data, variables) => {
      // Revalidar conversación si es conocida
      if (variables.conversation_id) {
        queryClient.invalidateQueries({
          queryKey: ['messages', 'conversation', variables.conversation_id],
        });
      }
      // Revalidar lista de mensajes
      queryClient.invalidateQueries({ queryKey: ['messages'] });
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
 * Hook para crear una nueva conversación
 * Invalida lista de mensajes
 * 
 * @param {object} options - { onSuccess, onError }
 * @returns { mutate, isPending, isError, error, data }
 */
export function useCreateConversation(options = {}) {
  const { onSuccess = null, onError = null } = options;
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload) =>
      apiClient.post('/api/v1/mensajeria/crear-conversacion/', payload),
    onSuccess: (data) => {
      // Revalidar lista de mensajes
      queryClient.invalidateQueries({ queryKey: ['messages'] });
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
 * Hook para eliminar un mensaje (si el usuario tiene permiso)
 * Invalida conversación y lista de mensajes
 * 
 * @param {object} options - { onSuccess, onError }
 * @returns { mutate, isPending, isError, error }
 */
export function useDeleteMessage(options = {}) {
  const { onSuccess = null, onError = null } = options;
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (messageId) =>
      apiClient.delete(`/api/v1/mensajeria/mensaje/${messageId}/`),
    onSuccess: (data) => {
      // Revalidar todas las conversaciones y mensajes
      queryClient.invalidateQueries({ queryKey: ['messages'] });
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
