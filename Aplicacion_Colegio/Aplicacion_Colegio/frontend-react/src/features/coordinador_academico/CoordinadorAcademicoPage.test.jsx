import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, postMock , setupUser } from '../../test/test-utils';

import CoordinadorAcademicoPage from './CoordinadorAcademicoPage';

describe('CoordinadorAcademicoPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getMock.mockResolvedValue({ planificaciones: [] });
  });

  it('shows loading state while plans are loading', () => {
    getMock.mockReturnValueOnce(new Promise(() => {}));

    setupUser([]);
    renderWithProviders(<CoordinadorAcademicoPage />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('disables update button without PLANNING_APPROVE', async () => {
    setupUser([]);
    renderWithProviders(<CoordinadorAcademicoPage />);

    await screen.findByText('Sin planificaciones pendientes.');

    const button = screen.getByRole('button', { name: 'Actualizar' });
    expect(button).toBeDisabled();
  });

  it('submits planning status update with PLANNING_APPROVE', async () => {
    const user = userEvent.setup({ delay: null });
    postMock.mockResolvedValueOnce({ message: 'Planificacion aprobada correctamente' });

    setupUser(['PLANNING_APPROVE']);
    renderWithProviders(<CoordinadorAcademicoPage />);

    await screen.findByText('Sin planificaciones pendientes.');

    await user.type(screen.getByLabelText('Planificacion ID'), '9');
    await user.type(screen.getByLabelText('Observaciones'), 'Revision curricular ok');
    await user.click(screen.getByRole('button', { name: 'Actualizar' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/coordinador/planificaciones/9/estado/', {
        estado: 'APROBADA',
        observaciones: 'Revision curricular ok',
      });
    });
  });

  it('shows backend error when update fails', async () => {
    const user = userEvent.setup({ delay: null });
    postMock.mockRejectedValueOnce({ payload: { detail: 'No se pudo actualizar' } });

    setupUser(['PLANNING_APPROVE']);
    renderWithProviders(<CoordinadorAcademicoPage />);

    await screen.findByText('Sin planificaciones pendientes.');

    await user.type(screen.getByLabelText('Planificacion ID'), '9');
    await user.click(screen.getByRole('button', { name: 'Actualizar' }));

    await waitFor(() => {
      expect(screen.getByText('No se pudo actualizar')).toBeInTheDocument();
    });
  });

  it('shows saving state while planning update is in progress', async () => {
    const user = userEvent.setup({ delay: null });
    postMock.mockReturnValueOnce(new Promise(() => {}));

    setupUser(['PLANNING_APPROVE']);
    renderWithProviders(<CoordinadorAcademicoPage />);

    await screen.findByText('Sin planificaciones pendientes.');

    await user.type(screen.getByLabelText('Planificacion ID'), '9');
    await user.click(screen.getByRole('button', { name: 'Actualizar' }));

    expect(screen.getByRole('button', { name: 'Guardando...' })).toBeDisabled();
  });
});
