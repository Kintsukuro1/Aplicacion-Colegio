import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.unmock('@/services/apiClient');

import { apiClient } from './apiClient';
import { clearTokens, setTokens } from '@/stores/authStore';

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'ERROR',
    async json() {
      return payload;
    },
  };
}

describe('apiClient JWT flow', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    clearTokens();
  });

  it('attaches bearer token from store', async () => {
    setTokens({ access: 'access-1', refresh: 'refresh-1' });
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(jsonResponse(200, { ok: true }));

    await apiClient.get('/api/v1/me/');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe('Bearer access-1');
  });

  it('refreshes token and retries request after 401', async () => {
    setTokens({ access: 'expired-access', refresh: 'refresh-1' });

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (url.endsWith('/api/v1/auth/token/refresh/')) {
        return jsonResponse(200, { access: 'fresh-access', refresh: 'refresh-2' });
      }
      const authHeader = fetchMock.mock.calls.at(-1)?.[1]?.headers?.Authorization;
      if (authHeader === 'Bearer expired-access') {
        return jsonResponse(401, { detail: 'expired' });
      }
      return jsonResponse(200, { ok: true });
    });

    const payload = await apiClient.get('/api/v1/me/');

    expect(payload).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(localStorage.getItem('ac_access_token')).toBe('fresh-access');
    expect(localStorage.getItem('ac_refresh_token')).toBe('refresh-2');
  });

  it('reuses a single refresh request for concurrent 401 responses', async () => {
    setTokens({ access: 'expired-access', refresh: 'refresh-1' });

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
      if (url.endsWith('/api/v1/auth/token/refresh/')) {
        return jsonResponse(200, { access: 'fresh-access', refresh: 'refresh-2' });
      }

      const authHeader = options.headers?.Authorization;
      if (authHeader === 'Bearer expired-access') {
        return jsonResponse(401, { detail: 'expired' });
      }
      return jsonResponse(200, { ok: true });
    });

    const [one, two] = await Promise.all([
      apiClient.get('/api/v1/me/'),
      apiClient.get('/api/v1/dashboard/resumen/'),
    ]);

    expect(one).toEqual({ ok: true });
    expect(two).toEqual({ ok: true });

    const refreshCalls = fetchMock.mock.calls.filter(([url]) => url.endsWith('/api/v1/auth/token/refresh/'));
    expect(refreshCalls).toHaveLength(1);
  });

  it('clears tokens when refresh fails', async () => {
    setTokens({ access: 'expired-access', refresh: 'refresh-1' });

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options = {}) => {
      if (url.endsWith('/api/v1/auth/token/refresh/')) {
        return jsonResponse(401, { detail: 'invalid refresh' });
      }

      const authHeader = options.headers?.Authorization;
      if (authHeader === 'Bearer expired-access') {
        return jsonResponse(401, { detail: 'expired' });
      }
      return jsonResponse(200, { ok: true });
    });

    await expect(apiClient.get('/api/v1/me/')).rejects.toThrow('Token refresh failed');
    expect(localStorage.getItem('ac_access_token')).toBeNull();
    expect(localStorage.getItem('ac_refresh_token')).toBeNull();
  });
});
