import '@testing-library/jest-dom/vitest';
import { vi, afterEach } from 'vitest';
import { getMock, postMock, patchMock, deleteMock, clearQueryClients } from './test-utils';
import { useAuthStore } from '../stores/useAuthStore';

// Global mock for API client
vi.mock('@/services/apiClient', () => ({
  apiClient: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: (...args) => patchMock(...args),
    del: (...args) => deleteMock(...args),
  },
}));

// Global teardown for all tests
afterEach(async () => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
  deleteMock.mockReset();
  vi.clearAllMocks();
  await clearQueryClients();
  useAuthStore.setState({
    user: null,
    isAuthenticated: false,
  });
});
