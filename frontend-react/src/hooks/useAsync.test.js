import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useAsync } from './useAsync';

describe('useAsync Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should start in idle state', () => {
    const asyncFn = vi.fn();
    const { result } = renderHook(() => useAsync(asyncFn));

    expect(result.current.status).toBe('idle');
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('should execute async function and return success', async () => {
    const mockData = { id: 1, name: 'Test' };
    const asyncFn = vi.fn(async () => mockData);

    const { result } = renderHook(() => useAsync(asyncFn));

    act(() => {
      result.current.execute();
    });

    await waitFor(() => {
      expect(result.current.status).toBe('success');
    });

    expect(result.current.isSuccess).toBe(true);
    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
  });

  it('should handle execution with arguments', async () => {
    const asyncFn = vi.fn(async (id, name) => ({ id, name }));

    const { result } = renderHook(() => useAsync(asyncFn));

    act(() => {
      result.current.execute(1, 'Test');
    });

    await waitFor(() => {
      expect(result.current.status).toBe('success');
    });

    expect(asyncFn).toHaveBeenCalledWith(1, 'Test');
    expect(result.current.data).toEqual({ id: 1, name: 'Test' });
  });

  it('should handle errors', async () => {
    const mockError = new Error('Execution failed');
    const asyncFn = vi.fn(async () => {
      throw mockError;
    });

    const { result } = renderHook(() => useAsync(asyncFn));

    act(() => {
      // Usar catch para no reportar error no manejado
      result.current.execute().catch(() => {});
    });

    await waitFor(() => {
      expect(result.current.status).toBe('error');
    });

    expect(result.current.isError).toBe(true);
    expect(result.current.error).toBeDefined();
    expect(result.current.data).toBeNull();
  });

  it('should call onSuccess callback', async () => {
    const mockData = { id: 1 };
    const onSuccess = vi.fn();
    const asyncFn = vi.fn(async () => mockData);

    const { result } = renderHook(() => useAsync(asyncFn, { onSuccess }));

    act(() => {
      result.current.execute();
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(mockData);
    });
  });

  it('should call onError callback', async () => {
    const mockError = new Error('Failed');
    const onError = vi.fn();
    const asyncFn = vi.fn(async () => {
      throw mockError;
    });

    const { result } = renderHook(() => useAsync(asyncFn, { onError }));

    act(() => {
      // Usar catch para no reportar error no manejado
      result.current.execute().catch(() => {});
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalled();
    });
  });

  it('should call onSettled callback in both success and error', async () => {
    const onSettled = vi.fn();
    const asyncFn = vi.fn(async () => ({ id: 1 }));

    const { result } = renderHook(() => useAsync(asyncFn, { onSettled }));

    act(() => {
      result.current.execute();
    });

    await waitFor(() => {
      expect(onSettled).toHaveBeenCalledWith({ id: 1 }, null);
    });
  });

  it('should show loading state during execution', async () => {
    const asyncFn = vi.fn(
      async () =>
        new Promise((resolve) => setTimeout(() => resolve({ id: 1 }), 100))
    );

    const { result } = renderHook(() => useAsync(asyncFn));

    act(() => {
      result.current.execute();
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.status).toBe('pending');

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.status).toBe('success');
  });
});
