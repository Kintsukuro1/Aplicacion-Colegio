import { useState, useCallback } from 'react';

/**
 * Hook para manejar operaciones async (POST, PUT, PATCH, DELETE)
 * Gestiona estados: idle, pending, success, error
 *
 * @param {function} asyncFunction - Función async que retorna una promesa
 *   (ej: async () => await apiClient.post('/api/v1/tarea/', data))
 * @param {object} options - Opciones adicionales
 *   - onSuccess: (result) => void - callback cuando completa exitosamente
 *   - onError: (error) => void - callback cuando falla
 *   - onSettled: (result, error) => void - callback final (siempre se ejecuta)
 *
 * @returns {object} {
 *   execute, data, error, status, isLoading, isSuccess, isError
 * }
 * - execute(...args) - llama la función async con args
 * - data - resultado de la última ejecución exitosa
 * - error - error de la última ejecución
 * - status - 'idle' | 'pending' | 'success' | 'error'
 * - isLoading - true si está en progreso
 * - isSuccess - true si última ejecución fue exitosa
 * - isError - true si última ejecución falló
 */
export function useAsync(asyncFunction, options = {}) {
  const {
    onSuccess = null,
    onError = null,
    onSettled = null,
  } = options;

  const [status, setStatus] = useState('idle');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const execute = useCallback(
    async (...args) => {
      setStatus('pending');
      setData(null);
      setError(null);

      try {
        const result = await asyncFunction(...args);
        setData(result);
        setStatus('success');
        if (onSuccess) onSuccess(result);
        if (onSettled) onSettled(result, null);
        return result;
      } catch (err) {
        const errorMsg = err?.message || 'An error occurred';
        setError(errorMsg);
        setStatus('error');
        if (onError) onError(err);
        if (onSettled) onSettled(null, err);
        throw err; // Re-throw para que el caller pueda manejar si lo necesita
      }
    },
    [asyncFunction, onSuccess, onError, onSettled]
  );

  return {
    execute,
    data,
    error,
    status,
    isLoading: status === 'pending',
    isSuccess: status === 'success',
    isError: status === 'error',
  };
}
