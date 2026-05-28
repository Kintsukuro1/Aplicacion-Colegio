const ACCESS_KEY = 'ac_access_token';
const REFRESH_KEY = 'ac_refresh_token';

// Decode JWT payload without external library
function decodeJWT(token) {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    
    const payload = JSON.parse(atob(parts[1]));
    return payload;
  } catch (e) {
    console.error('[Auth] Failed to decode JWT:', e);
    return null;
  }
}

// Check if token has expired based on JWT exp claim
export function isTokenExpired(token) {
  if (!token) return true;
  
  const payload = decodeJWT(token);
  if (!payload || !payload.exp) return true;
  
  // exp is in seconds, Date.now() is in milliseconds
  const expiresAt = payload.exp * 1000;
  const now = Date.now();
  
  // Consider expired if less than 1 minute remaining
  const bufferMs = 60 * 1000;
  return now >= (expiresAt - bufferMs);
}

// Get token info (useful for debugging)
export function getTokenInfo(token) {
  if (!token) return null;
  
  const payload = decodeJWT(token);
  if (!payload) return null;
  
  return {
    subject: payload.sub,
    expiresAt: new Date(payload.exp * 1000),
    isExpired: isTokenExpired(token),
    expiresIn: Math.max(0, Math.floor((payload.exp * 1000 - Date.now()) / 1000)),
  };
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens({ access, refresh }) {
  if (access) {
    localStorage.setItem(ACCESS_KEY, access);
  }
  if (refresh) {
    localStorage.setItem(REFRESH_KEY, refresh);
  }
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function isAuthenticated() {
  const token = getAccessToken();
  return Boolean(token) && !isTokenExpired(token);
}

// Multi-tab synchronization: Clear tokens if cleared in another tab
export function initMultiTabSync() {
  const handleStorageChange = (event) => {
    // If access token was cleared in another tab, clear it here too
    if (event.key === ACCESS_KEY && event.newValue === null) {
      // Token was removed in another tab
      localStorage.removeItem(REFRESH_KEY);
      // Dispatch custom event so app can react to logout
      window.dispatchEvent(new CustomEvent('auth-logout', { detail: 'multi-tab-sync' }));
    }
  };
  
  window.addEventListener('storage', handleStorageChange);
  
  // Return cleanup function
  return () => {
    window.removeEventListener('storage', handleStorageChange);
  };
}

