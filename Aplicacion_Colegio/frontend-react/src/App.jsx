import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { MotionConfig } from 'framer-motion';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { AppSidebar } from './components/layout/AppSidebar';
import MobileBottomNav from './components/layout/MobileBottomNav';
import NotificationBell from './components/feedback/NotificationBell';
import ProtectedRoute from './components/auth/ProtectedRoute';
import { ToastProvider } from './components/feedback/Toast';
import { UpdateListener } from './components/utils/UpdateListener';
import { apiClient } from './services/apiClient';
import { clearTokens, getRefreshToken } from './stores/authStore';
import { canAccessRoute } from './utils/capabilities';
import { useAuthStore } from './stores/useAuthStore';
import { APP_ROUTES } from './routes/appRoutes';

const ReactQueryDevtools = import.meta.env.DEV
  ? lazy(() =>
      import('@tanstack/react-query-devtools').then((module) => ({
        default: module.ReactQueryDevtools,
      }))
    )
  : null;
// Eager load only public/login pages if desired, but we can lazy load them too for max savings
const LoginPage = lazy(() => import('./features/auth/LoginPage'));
const RegisterPage = lazy(() => import('./features/auth/RegisterPage'));

function AccessDeniedPage() {
  return (
    <section>
      <header className="page-header">
        <div>
          <h2>Acceso Denegado</h2>
          <p>No tienes capabilities para acceder a esta ruta.</p>
        </div>
      </header>
    </section>
  );
}

function FallbackRedirect({ visibleRoutes }) {
  const fallback = visibleRoutes[0]?.to;
  if (!fallback) {
    return <AccessDeniedPage />;
  }

  return <Navigate to={fallback} replace />;
}

function PageLoader() {
  return (
    <div style={{ padding: '2rem', display: 'flex', gap: '1rem', flexDirection: 'column' }}>
      <div style={{ height: '40px', width: '200px', backgroundColor: 'var(--surface-color)', borderRadius: 'var(--radius-md)' }} />
      <div style={{ height: '300px', width: '100%', backgroundColor: 'var(--surface-color)', borderRadius: 'var(--radius-lg)' }} />
    </div>
  );
}

function ShellLayout({ children, visibleRoutes }) {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') {
      document.body.style.overflow = sidebarOpen ? 'hidden' : '';
      return () => {
        document.body.style.overflow = '';
      };
    }

    const mobileQuery = window.matchMedia('(max-width: 768px)');
    const syncBodyScroll = () => {
      document.body.style.overflow = sidebarOpen && mobileQuery.matches ? 'hidden' : '';
    };

    syncBodyScroll();
    if (typeof mobileQuery.addEventListener === 'function') {
      mobileQuery.addEventListener('change', syncBodyScroll);
    } else {
      mobileQuery.addListener(syncBodyScroll);
    }

    return () => {
      document.body.style.overflow = '';
      if (typeof mobileQuery.removeEventListener === 'function') {
        mobileQuery.removeEventListener('change', syncBodyScroll);
      } else {
        mobileQuery.removeListener(syncBodyScroll);
      }
    };
  }, [sidebarOpen]);

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === 'Escape') {
        setSidebarOpen(false);
      }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, []);

  async function onLogout() {
    try {
      const refresh = getRefreshToken();
      if (refresh) {
        await apiClient.post('/api/v1/auth/logout/', { refresh });
      }
    } catch {
      // Logout local debe continuar incluso si falla la revocacion remota.
    } finally {
      const logoutStore = useAuthStore.getState().logout;
      logoutStore();
      navigate('/login', { replace: true });
    }
  }

  return (
    <div className="app-shell">
      {/* Mobile overlay backdrop */}
      <div
        className={`sidebar-overlay${sidebarOpen ? ' sidebar-overlay-visible' : ''}`}
        onClick={closeSidebar}
        aria-hidden="true"
      />

      <AppSidebar
        visibleRoutes={visibleRoutes}
        onLogout={onLogout}
        isOpen={sidebarOpen}
        onClose={closeSidebar}
      />

      <main>
        <div className="main-topbar">
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={() => setSidebarOpen(true)}
            aria-label="Abrir menu"
            aria-expanded={sidebarOpen}
            aria-controls="primary-sidebar"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <NotificationBell />
        </div>
        {children}
      </main>

      <MobileBottomNav visibleRoutes={visibleRoutes} />
    </div>
  );
}

function GuardedPage({ route }) {
  const me = useAuthStore((state) => state.user);
  if (!canAccessRoute(me, route)) {
    return <AccessDeniedPage />;
  }

  const Component = route.component;
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

function AuthorizedApp() {
  const logout = useAuthStore((state) => state.logout);
  const setMe = useAuthStore((state) => state.setUser);
  
  const { data: mePayload, isLoading: loadingMe } = useQuery({
    queryKey: ['me'],
    queryFn: () => apiClient.get('/api/v1/me/'),
    retry: false,
  });

  // Sync me payload to Zustand during render (not in useEffect)
  const syncedMeRef = useMemo(() => ({ current: null }), []);
  if (mePayload && mePayload !== syncedMeRef.current) {
    syncedMeRef.current = mePayload;
    setMe(mePayload);
  }

  // Listen for multi-tab logout events
  useEffect(() => {
    const handleRemoteLogout = (event) => {
      console.info('[Auth] Remote logout detected:', event.detail);
      logout();
    };

    window.addEventListener('auth-logout', handleRemoteLogout);
    return () => {
      window.removeEventListener('auth-logout', handleRemoteLogout);
    };
  }, [logout]);

  const visibleRoutes = useMemo(() => {
    if (!mePayload) {
      return [];
    }
    return APP_ROUTES.filter((route) => canAccessRoute(mePayload, route));
  }, [mePayload]);

  return loadingMe ? (
    <section>
      <p>Cargando sesión…</p>
    </section>
  ) : !mePayload && !loadingMe ? (
    <Navigate to="/login" replace />
  ) : (
    <>
      <UpdateListener />
      <ShellLayout visibleRoutes={visibleRoutes}>
        <Routes>
          {APP_ROUTES.map((route) => (
            <Route
              key={route.path}
              path={route.path}
              element={<GuardedPage route={route} />}
            />
          ))}
          <Route path="*" element={<FallbackRedirect visibleRoutes={visibleRoutes} />} />
        </Routes>
      </ShellLayout>
    </>
  );
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <Suspense fallback={<div className="page-loader">Cargando aplicación…</div>}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AuthorizedApp />
                </ProtectedRoute>
              }
            />
          </Routes>
        </Suspense>
        {ReactQueryDevtools ? (
          <Suspense fallback={null}>
            <ReactQueryDevtools initialIsOpen={false} />
          </Suspense>
        ) : null}
      </ToastProvider>
    </MotionConfig>
  );
}
