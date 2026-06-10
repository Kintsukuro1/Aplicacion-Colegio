import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, postMock , setupUser } from '../../test/test-utils';

import ActiveSessionsPage from './ActiveSessionsPage';

describe('ActiveSessionsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    getMock.mockImplementation((path) => {
      if (path === '/api/v1/seguridad/sesiones-activas/') {
        return Promise.resolve({
          sesiones: [
            {
              id: 11,
              user_email: 'admin@colegio.cl',
              user_rol: 'Administrador escolar',
              colegio_rbd: 10001,
              ip: '192.168.0.10',
              dispositivo: 'Desktop',
              ultima_actividad: '2026-04-05T12:00:00Z',
            },
          ],
        });
      }

      if (path === '/api/v1/seguridad/dashboard/') {
        return Promise.resolve({
          colegio: 'Colegio Santa Maria',
          intentos_fallidos_24h: 2,
          ips_bloqueadas: 1,
          sesiones_activas: 1,
          accesos_datos_sensibles_24h: 3,
          ips_bloqueadas_lista: ['10.0.0.8'],
        });
      }

      return Promise.resolve({});
    });
  });

  it('shows access denied without capabilities', async () => {
    setupUser([]);
    renderWithProviders(<ActiveSessionsPage />);
    expect(await screen.findByText('No tienes permisos para ver esta pagina.')).toBeInTheDocument();
  });

  it('loads sessions and revokes a selected session', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    postMock.mockResolvedValue({ detail: 'Sesion revocada exitosamente.' });

    setupUser(['AUDIT_VIEW']);
    renderWithProviders(<ActiveSessionsPage />);

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/seguridad/sesiones-activas/');
      expect(getMock).toHaveBeenCalledWith('/api/v1/seguridad/dashboard/');
    });

    expect(screen.getAllByText('Sesiones activas').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('IPs bloqueadas').length).toBeGreaterThanOrEqual(1);

    const revokeButton = await screen.findByRole('button', { name: 'Revocar' });
    await user.click(revokeButton);

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/seguridad/sesiones/11/revocar/', {});
    });
  });

  it('unblocks an IP from blocked list', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    postMock.mockResolvedValue({ detail: 'IP desbloqueada correctamente.' });

    setupUser(['SYSTEM_ADMIN']);
    renderWithProviders(<ActiveSessionsPage />);

    const unblockButton = await screen.findByRole('button', { name: 'Desbloquear' });
    await user.click(unblockButton);

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/seguridad/desbloquear-ip/', { ip: '10.0.0.8' });
    });
  });
});
