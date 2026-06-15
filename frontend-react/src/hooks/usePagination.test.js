import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { usePagination } from './usePagination';

const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('@/services/apiClient', () => ({
  apiClient: {
    get: mockGet,
  },
}));

describe('usePagination Hook', () => {
  const createWrapper = () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return ({ children }) => React.createElement(QueryClientProvider, { client: queryClient }, children);
  };

  beforeEach(() => {
    mockGet.mockReset();
  });

  it('should fetch initial page', async () => {
    const mockData = {
      results: [{ id: 1 }, { id: 2 }],
      count: 20,
    };
    mockGet.mockResolvedValue(mockData);

    const { result } = renderHook(() => usePagination('/api/items'), { wrapper: createWrapper() });

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.items).toEqual([{ id: 1 }, { id: 2 }]);
    expect(result.current.pagination.total).toBe(20);
    expect(result.current.pagination.currentPage).toBe(1);
  });

  it('should navigate to next page', async () => {
    const mockData = {
      results: [{ id: 1 }, { id: 2 }],
      count: 30,
    };
    mockGet.mockResolvedValue(mockData);

    const { result } = renderHook(() => usePagination('/api/items', { initialLimit: 10 }), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.pagination.currentPage).toBe(1);

    act(() => {
      result.current.nextPage();
    });

    await waitFor(() => {
      expect(result.current.pagination.currentPage).toBe(2);
      expect(result.current.pagination.offset).toBe(10);
    });
  });

  it('should navigate to previous page', async () => {
    const mockData = {
      results: [{ id: 1 }, { id: 2 }],
      count: 30,
    };
    mockGet.mockResolvedValue(mockData);

    const { result } = renderHook(() => usePagination('/api/items', { initialLimit: 10 }), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    act(() => {
      result.current.nextPage();
    });

    await waitFor(() => {
      expect(result.current.pagination.currentPage).toBe(2);
    });

    act(() => {
      result.current.prevPage();
    });

    await waitFor(() => {
      expect(result.current.pagination.currentPage).toBe(1);
    });
  });

  it('should calculate totalPages correctly', async () => {
    const mockData = {
      results: Array.from({ length: 10 }, (_, i) => ({ id: i })),
      count: 25,
    };
    mockGet.mockResolvedValue(mockData);

    const { result } = renderHook(() => usePagination('/api/items', { initialLimit: 10 }), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.pagination.totalPages).toBe(3); // 25 / 10 = 2.5 → 3
  });

  it('should handle setLimit and reset to page 0', async () => {
    const mockData = {
      results: [{ id: 1 }, { id: 2 }],
      count: 50,
    };
    mockGet.mockResolvedValue(mockData);

    const { result } = renderHook(() => usePagination('/api/items', { initialLimit: 10 }), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.pagination.limit).toBe(10);
    });

    act(() => {
      result.current.setLimit(20);
    });

    await waitFor(() => {
      expect(result.current.pagination.limit).toBe(20);
      expect(result.current.pagination.currentPage).toBe(1);
    });
  });

  it('should call onSuccess callback', async () => {
    const mockData = {
      results: [{ id: 1 }],
      count: 10,
    };
    const onSuccess = vi.fn();
    mockGet.mockResolvedValue(mockData);

    renderHook(() => usePagination('/api/items', { onSuccess }), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith([{ id: 1 }], 10);
    });
  });

  it('should not allow next page when on last page', async () => {
    const mockData = {
      results: [{ id: 1 }],
      count: 5,
    };
    mockGet.mockResolvedValue(mockData);

    const { result } = renderHook(() => usePagination('/api/items', { initialLimit: 10 }), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Solo hay 1 página (5 items / 10 limit)
    expect(result.current.pagination.totalPages).toBe(1);
    expect(result.current.pagination.currentPage).toBe(1);

    // Intentar ir a siguiente página no debe hacer nada
    act(() => {
      result.current.nextPage();
    });

    expect(result.current.pagination.currentPage).toBe(1);
  });
});
