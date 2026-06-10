import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useFetch } from './useFetch';

const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('@/services/apiClient', () => ({
  apiClient: {
    get: mockGet,
  },
}));

describe('useFetch Hook', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('should fetch data and return it', async () => {
    const mockData = { id: 1, name: 'Test' };
    mockGet.mockResolvedValue(mockData);

    const { result } = renderHook(() => useFetch('/api/test'));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
  });

  it('should handle errors', async () => {
    const mockError = new Error('API Error');
    mockGet.mockRejectedValue(mockError);

    const { result } = renderHook(() => useFetch('/api/test'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.data).toBeNull();
  });

  it('should skip fetch when skip=true', async () => {
    mockGet.mockResolvedValue({ id: 1 });

    const { result } = renderHook(() => useFetch('/api/test', { skip: true }));

    expect(result.current.loading).toBe(false);
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('should call refetch and get fresh data', async () => {
    const mockData1 = { id: 1 };
    const mockData2 = { id: 2 };
    mockGet.mockResolvedValueOnce(mockData1).mockResolvedValueOnce(mockData2);

    const { result } = renderHook(() => useFetch('/api/test-refetch'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockData1);

    // Clear and set up new mock for refetch
    mockGet.mockClear();
    mockGet.mockResolvedValueOnce(mockData2);

    result.current.refetch();

    await waitFor(() => {
      expect(result.current.data).toEqual(mockData2);
    });
  });

  it('should call onSuccess callback', async () => {
    // Limpiar completamente antes de este test
    mockGet.mockClear();
    mockGet.mockReset();

    const mockData = { id: 1 };
    const onSuccess = vi.fn();
    mockGet.mockResolvedValue(mockData);

    const { result } = renderHook(() => useFetch('/api/callback-success', { onSuccess }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(onSuccess).toHaveBeenCalledWith(mockData);
  });

  it('should call onError callback', async () => {
    const mockError = new Error('API Error');
    const onError = vi.fn();
    mockGet.mockRejectedValue(mockError); // No usar ValueOnce

    const { result } = renderHook(() => useFetch('/api/test-error', { onError }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(onError).toHaveBeenCalled();
  });
});
