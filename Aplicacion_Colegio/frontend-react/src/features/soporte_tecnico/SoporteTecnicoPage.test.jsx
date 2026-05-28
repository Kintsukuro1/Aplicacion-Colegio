import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderWithProviders, postMock, setupUser, clearUser } from '../../test/test-utils';
import SoporteTecnicoPage from './SoporteTecnicoPage';

describe('SoporteTecnicoPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setupUser(['SUPPORT_CREATE_TICKET']);
  });
  it('disables create ticket action without SUPPORT_CREATE_TICKET', () => {
    setupUser([]);

    renderWithProviders(<SoporteTecnicoPage />);

    expect(screen.getByText('Crear tickets')).toBeInTheDocument();
    expect(screen.getAllByText('Bloqueado').length).toBeGreaterThanOrEqual(1);

    const button = screen.getByRole('button', { name: 'Crear ticket' });
    expect(button).toBeDisabled();
  });

  it('submits create ticket when capability exists', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValueOnce({ message: 'Ticket creado correctamente.', id: 55 });

    renderWithProviders(<SoporteTecnicoPage />);

    await user.type(screen.getByLabelText('Titulo'), 'Error login');
    await user.type(screen.getByLabelText('Descripcion'), 'No me deja entrar');
    await user.click(screen.getByRole('button', { name: 'Crear ticket' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/soporte/tickets/crear/', {
        titulo: 'Error login',
        descripcion: 'No me deja entrar',
        categoria: 'OTRO',
        prioridad: 'MEDIA',
      });
    });

    expect(screen.getByText('Ticket creado correctamente.')).toBeInTheDocument();
    expect(screen.getByLabelText('Ticket ID')).toHaveValue(55);
  });

  it('disables reset flow without reset capabilities', () => {
    renderWithProviders(<SoporteTecnicoPage />);

    const submitButton = screen.getByRole('button', { name: 'Ejecutar flujo reset' });

    expect(submitButton).toBeDisabled();
    expect(postMock).not.toHaveBeenCalled();
  });
});
