import { QueryClient } from '@tanstack/react-query';

/**
 * QueryClient configurado para Aplicación Colegio
 * 
 * Defaults:
 * - staleTime: 5 minutos - tiempo antes de considerar datos como "stale"
 * - gcTime: 10 minutos - tiempo de vida en caché después de unmount
 * - retry: 2 intentos con backoff exponencial para fallos de red
 * - refetchOnWindowFocus: true - revalidar cuando la ventana recupera foco
 * - refetchOnMount: "stale" - revalidar solo si los datos están stale al montar
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutos
      gcTime: 1000 * 60 * 10, // 10 minutos (anteriormente cacheTime)
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: true,
      refetchOnMount: 'stale',
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
      retryDelay: 1000,
    },
  },
});
