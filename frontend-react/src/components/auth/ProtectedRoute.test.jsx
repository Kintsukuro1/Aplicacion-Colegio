import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import ProtectedRoute from './ProtectedRoute';

const isAuthenticatedMock = vi.fn();

vi.mock('../../stores/authStore', () => ({
  isAuthenticated: () => isAuthenticatedMock(),
}));

describe('ProtectedRoute', () => {
  beforeEach(() => {
    isAuthenticatedMock.mockReset();
  });

  it('redirects to /login when unauthenticated', () => {
    isAuthenticatedMock.mockReturnValue(false);

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Private page</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Login page')).toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    isAuthenticatedMock.mockReturnValue(true);

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Private page</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Private page')).toBeInTheDocument();
  });
});
