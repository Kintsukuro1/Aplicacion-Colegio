import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '@/stores/authStore';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
let refreshInFlight = null;

async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) {
    throw new Error('No refresh token available');
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/auth/token/refresh/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    clearTokens();
    throw new Error('Token refresh failed');
  }

  const payload = await response.json();
  setTokens({ access: payload.access, refresh: payload.refresh || refresh });
  return payload.access;
}

async function getOrRefreshAccessToken() {
  if (!refreshInFlight) {
    refreshInFlight = refreshAccessToken().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function request(path, options = {}, attemptRefresh = true) {
  const access = getAccessToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (access) {
    headers.Authorization = `Bearer ${access}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && attemptRefresh && getRefreshToken()) {
    const nextAccess = await getOrRefreshAccessToken();
    return request(
      path,
      {
        ...options,
        headers: {
          ...(options.headers || {}),
          Authorization: `Bearer ${nextAccess}`,
        },
      },
      false
    );
  }

  if (!response.ok) {
    let errorPayload = null;
    try {
      errorPayload = await response.json();
    } catch {
      errorPayload = { detail: response.statusText };
    }
    const error = new Error(errorPayload.detail || 'Request failed');
    error.status = response.status;
    error.payload = errorPayload;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const apiClient = {
  get: (path) => request(path, { method: 'GET' }),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  del: (path) => request(path, { method: 'DELETE' }),
  baseUrl: API_BASE_URL,
};
