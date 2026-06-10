import { render } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';

import { useAuthStore } from '../stores/useAuthStore';
import { ToastProvider } from '../components/feedback/Toast';

// ---------------------------------------------------------------------------
// Centralized API mocks
// ---------------------------------------------------------------------------

export const getMock = vi.fn();
export const postMock = vi.fn();
export const patchMock = vi.fn();
export const deleteMock = vi.fn();

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

/**
 * Configures the auth store with the given capabilities and optional user data.
 * Call in `beforeEach` or at the top of each `it()` block.
 *
 * @param {string[]} capabilities - Array of capability strings (e.g. ['COURSE_VIEW'])
 * @param {Object}   extras       - Additional user fields (role, email, etc.)
 * @returns {Object} The user object that was set in the store
 *
 * @example
 *   setupUser(['COURSE_VIEW', 'COURSE_CREATE']);
 *   setupUser(['SYSTEM_ADMIN'], { role: 'admin', email: 'admin@test.cl' });
 */
export function setupUser(capabilities = [], extras = {}) {
  const user = { capabilities, ...extras };
  useAuthStore.getState().setUser(user);
  return user;
}

/**
 * Clears the auth store. Already handled by global `afterEach` in setupTests.js,
 * but exported for cases where you need to clear mid-test.
 */
export function clearUser() {
  useAuthStore.getState().setUser(null);
}

// ---------------------------------------------------------------------------
// QueryClient helpers
// ---------------------------------------------------------------------------

const queryClients = [];

/**
 * Creates a fresh QueryClient configured for testing:
 * - No retries
 * - No garbage collection delay
 * - No background refetching
 */
export function createTestQueryClient() {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
        refetchOnMount: false,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
      },
    },
  });
  queryClients.push(client);
  return client;
}

export async function clearQueryClients() {
  await Promise.all(queryClients.map((client) => client.cancelQueries()));
  queryClients.forEach((client) => client.unmount());
  queryClients.forEach((client) => client.clear());
  queryClients.length = 0;
}

// ---------------------------------------------------------------------------
// API mock helpers
// ---------------------------------------------------------------------------

/**
 * Sets up `getMock` to return specific responses based on URL pattern matching.
 * Each key in `endpointMap` is checked via `url.includes(key)`.
 *
 * @param {Record<string, any>} endpointMap - Map of URL patterns to response data
 *
 * @example
 *   mockApiEndpoints({
 *     '/api/v1/cursos/': paginated([{ id_curso: 1, nombre: '5A' }]),
 *     '/api/v1/profesor/mi-horario/': { total_bloques: 4, horario: {} },
 *   });
 */
export function mockApiEndpoints(endpointMap) {
  getMock.mockImplementation((url) => {
    for (const [pattern, response] of Object.entries(endpointMap)) {
      if (url.includes(pattern)) {
        return Promise.resolve(
          typeof response === 'function' ? response(url) : response
        );
      }
    }
    return Promise.resolve({});
  });
}

// ---------------------------------------------------------------------------
// Response builders
// ---------------------------------------------------------------------------

/**
 * Builds a Django REST Framework paginated response.
 *
 * @param {Array}  results         - Array of result items
 * @param {Object} options
 * @param {number} [options.page]  - Current page number (for multi-page mocks)
 * @param {number} [options.total] - Override total count
 * @returns {{ count: number, next: string|null, previous: string|null, results: Array }}
 *
 * @example
 *   paginated([{ id: 1 }, { id: 2 }]);
 *   paginated([{ id: 1 }], { total: 25 }); // page 1 of 3
 */
export function paginated(results, { page = 1, total } = {}) {
  const count = total ?? results.length;
  const pageSize = 10;
  const hasNext = page * pageSize < count;
  const hasPrevious = page > 1;
  return {
    count,
    next: hasNext ? `?page=${page + 1}` : null,
    previous: hasPrevious ? `?page=${page - 1}` : null,
    results,
  };
}

/**
 * Creates a deferred promise for testing loading/async states.
 *
 * @returns {{ promise: Promise, resolve: Function, reject: Function }}
 *
 * @example
 *   const { promise, resolve } = createDeferred();
 *   getMock.mockReturnValue(promise);
 *   // ... assert loading state ...
 *   await act(async () => { resolve(data); });
 *   // ... assert loaded state ...
 */
export function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

// ---------------------------------------------------------------------------
// Render helper
// ---------------------------------------------------------------------------

/**
 * Renders a component wrapped in all necessary providers for testing.
 *
 * @param {React.ReactElement} ui - The component to render
 * @param {Object} options
 * @param {string}   [options.route='/']  - Initial URL for MemoryRouter
 * @param {string}   [options.path='/']   - Route path pattern for matching
 * @param {string[]} [options.user]       - Shortcut: capabilities array to set in auth store
 * @returns {import('@testing-library/react').RenderResult & { queryClient: QueryClient }}
 *
 * @example
 *   // Simple render with auth
 *   renderWithProviders(<MyPage />, { user: ['COURSE_VIEW'] });
 *
 *   // With route matching
 *   renderWithProviders(<CoursePage />, {
 *     user: ['COURSE_VIEW'],
 *     route: '/admin/cursos',
 *     path: '/admin/cursos',
 *   });
 */
export function renderWithProviders(ui, { route = '/', path = '/', user } = {}) {
  const queryClient = createTestQueryClient();
  const initialEntries = Array.isArray(route) ? route : [route];

  // Set up auth store if user capabilities provided via options
  if (user !== undefined) {
    const userData = Array.isArray(user) ? { capabilities: user } : user;
    useAuthStore.setState({
      user: userData,
      isAuthenticated: true,
    });
  }

  const rendered = render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={initialEntries}>
          <Routes>
            <Route path={path} element={ui} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>
  );

  return { ...rendered, queryClient };
}
