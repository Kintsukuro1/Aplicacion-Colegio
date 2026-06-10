import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, postMock } from '../../test/test-utils';

import LoginPage from './LoginPage';

const navigateMock = vi.fn();
const setTokensMock = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});



vi.mock('../../stores/authStore', () => ({
  setTokens: (...args) => setTokensMock(...args),
}));

describe('LoginPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    navigateMock.mockReset();
    setTokensMock.mockReset();
  });

  function renderLoginPage(route = '/login') {
    return renderWithProviders(<LoginPage />, {
      route,
      path: '/login',
    });
  }

  it('stores tokens and redirects after successful login', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValue({
      access: 'access-token',
      refresh: 'refresh-token',
    });

    renderLoginPage();

    await user.type(screen.getByLabelText('Correo'), 'admin@test.cl');
    await user.type(screen.getByLabelText('Contraseña'), 'Test#123456');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/auth/token/', {
        email: 'admin@test.cl',
        password: 'Test#123456',
      });
    });

    expect(setTokensMock).toHaveBeenCalledWith({ access: 'access-token', refresh: 'refresh-token' });
    expect(navigateMock).toHaveBeenCalledWith('/dashboard', { replace: true });
  });

  it('redirects back to the original route when login comes from a protected page', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValue({
      access: 'access-token',
      refresh: 'refresh-token',
    });

    renderLoginPage({
      pathname: '/login',
      state: { from: { pathname: '/profesor/clases' } },
    });

    await user.type(screen.getByLabelText('Correo'), 'profesor@test.cl');
    await user.type(screen.getByLabelText('Contraseña'), 'Test#123456');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalled();
    });

    expect(navigateMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/profesor\/clases|\/dashboard/),
      { replace: true }
    );
  });

  it('shows backend error when login fails', async () => {
    const user = userEvent.setup();
    postMock.mockRejectedValue({ payload: { detail: 'Credenciales invalidas' } });

    renderLoginPage();

    await user.type(screen.getByLabelText('Correo'), 'admin@test.cl');
    await user.type(screen.getByLabelText('Contraseña'), 'wrong');
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    await waitFor(() => {
      expect(screen.getByText('Credenciales invalidas')).toBeInTheDocument();
    });

    expect(setTokensMock).not.toHaveBeenCalled();
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it('shows local validation errors and avoids request when email is invalid', async () => {
    const user = userEvent.setup();

    renderLoginPage();

    await user.type(screen.getByLabelText('Correo'), 'correo-invalido');
    await user.click(screen.getByLabelText('Contraseña'));
    await user.tab();

    expect(screen.getByText('Ingresa un correo válido.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Ingresar' }));

    expect(postMock).not.toHaveBeenCalled();
  });
});
