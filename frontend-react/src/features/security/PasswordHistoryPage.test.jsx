import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock , setupUser } from '../../test/test-utils';

import PasswordHistoryPage from './PasswordHistoryPage';

describe('PasswordHistoryPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    getMock.mockImplementation((path) => {
      if (path === '/api/v1/seguridad/password-history/') {
        return Promise.resolve({
          entries: [
            {
              id: 5,
              user_email: 'admin@colegio.cl',
              user_rol: 'Administrador escolar',
              colegio_rbd: 10001,
              created_at: '2026-04-05T10:00:00Z',
            },
          ],
        });
      }

      if (path === '/api/v1/seguridad/auditoria-datos-sensibles/?dias=7') {
        return Promise.resolve({
          eventos: [
            {
              id: 9,
              timestamp: '2026-04-05T09:00:00Z',
              usuario: 'admin@colegio.cl',
              rol: 'Administrador escolar',
              modelo: 'PerfilEstudiante',
              object_id: 77,
              ip: '192.168.0.20',
              campos: ['rut', 'direccion'],
            },
          ],
        });
      }

      if (path === '/api/v1/seguridad/auditoria-datos-sensibles/?dias=15&modelo=PerfilEstudiante') {
        return Promise.resolve({
          eventos: [],
        });
      }

      return Promise.resolve({ entries: [], eventos: [] });
    });
  });

  it('shows access denied without capabilities', async () => {
    setupUser([]);
    renderWithProviders(<PasswordHistoryPage />);
    expect(await screen.findByText('No tienes permisos para ver esta pagina.')).toBeInTheDocument();
  });

  it('loads password history and sensitive audit on mount', async () => {
    setupUser(['AUDIT_VIEW']);
    renderWithProviders(<PasswordHistoryPage />);

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/seguridad/password-history/');
      expect(getMock).toHaveBeenCalledWith('/api/v1/seguridad/auditoria-datos-sensibles/?dias=7');
    });

    expect(screen.getAllByText('admin@colegio.cl').length).toBeGreaterThan(0);
    expect(screen.getByText('PerfilEstudiante')).toBeInTheDocument();
    expect(screen.getByText('Historial')).toBeInTheDocument();
    expect(screen.getByText('Auditoria')).toBeInTheDocument();
  });

  it('applies audit filters and requests filtered endpoint', async () => {
    const user = userEvent.setup();
    setupUser(['SYSTEM_ADMIN']);
    renderWithProviders(<PasswordHistoryPage />);

    const diasInput = await screen.findByLabelText('Dias');
    await user.clear(diasInput);
    await user.type(diasInput, '15');

    await user.type(screen.getByLabelText('Modelo'), 'PerfilEstudiante');
    await user.click(screen.getByRole('button', { name: 'Aplicar' }));

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/seguridad/auditoria-datos-sensibles/?dias=15&modelo=PerfilEstudiante');
    });

    await waitFor(() => {
      expect(screen.getByText('No hay accesos sensibles en el periodo consultado.')).toBeInTheDocument();
    });
  });
});
