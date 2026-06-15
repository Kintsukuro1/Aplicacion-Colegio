import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, postMock , setupUser } from '../../test/test-utils';

import PsicologoOrientadorPage from './PsicologoOrientadorPage';

describe('PsicologoOrientadorPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getMock.mockResolvedValue({ estudiantes: [{ id: 11, nombre_completo: 'Nina Soto' }] });
  });

  it('loads students on mount', async () => {
    setupUser(['COUNSELING_CREATE']);
    renderWithProviders(<PsicologoOrientadorPage />);

    expect(screen.getByRole('status')).toBeInTheDocument();

    await screen.findAllByText('Nina Soto');
    expect(getMock).toHaveBeenCalledWith('/api/psicologo/estudiantes/');
  });

  it('submits entrevista form with COUNSELING_CREATE', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValueOnce({ message: 'Entrevista creada.' });

    setupUser(['COUNSELING_CREATE']);
    renderWithProviders(<PsicologoOrientadorPage />);

    // Wait for students to load before interacting with the select
    await screen.findAllByText('Nina Soto');

    const studentSelects = screen.getAllByLabelText('Estudiante');
    await user.selectOptions(studentSelects[0], '11');
    await user.type(screen.getByLabelText('Fecha'), '2026-03-06');
    await user.type(screen.getByLabelText('Observaciones'), 'Seguimiento academico inicial');
    await user.click(screen.getByRole('button', { name: 'Registrar entrevista' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/psicologo/entrevistas/crear/', {
        estudiante_id: 11,
        fecha: '2026-03-06',
        motivo: 'ACADEMICO',
        observaciones: 'Seguimiento academico inicial',
        acuerdos: '',
        seguimiento_requerido: false,
      });
    });
  });

  it('disables update derivacion action without REFERRAL_EDIT', async () => {
    setupUser(['COUNSELING_CREATE']);
    renderWithProviders(<PsicologoOrientadorPage />);

    await screen.findAllByText('Nina Soto');

    const button = screen.getByRole('button', { name: 'Actualizar derivacion' });
    expect(button).toBeDisabled();
  });

  it('shows backend error when entrevista submit fails', async () => {
    const user = userEvent.setup();
    postMock.mockRejectedValueOnce({ payload: { error: 'Error de validacion' } });

    setupUser(['COUNSELING_CREATE']);
    renderWithProviders(<PsicologoOrientadorPage />);

    await screen.findAllByText('Nina Soto');
    const studentSelects = await screen.findAllByLabelText('Estudiante');
    await user.selectOptions(studentSelects[0], '11');
    await user.type(screen.getByLabelText('Fecha'), '2026-03-06');
    await user.type(screen.getByLabelText('Observaciones'), 'Seguimiento academico inicial');
    await user.click(screen.getByRole('button', { name: 'Registrar entrevista' }));

    await waitFor(() => {
      expect(screen.getByText('Error de validacion')).toBeInTheDocument();
    });
  });

  it('shows saving state while entrevista request is in progress', async () => {
    const user = userEvent.setup();
    postMock.mockReturnValueOnce(new Promise(() => {}));

    setupUser(['COUNSELING_CREATE']);
    renderWithProviders(<PsicologoOrientadorPage />);

    await screen.findAllByText('Nina Soto');
    const studentSelects = await screen.findAllByLabelText('Estudiante');
    await user.selectOptions(studentSelects[0], '11');
    await user.type(screen.getByLabelText('Fecha'), '2026-03-06');
    await user.type(screen.getByLabelText('Observaciones'), 'Seguimiento academico inicial');
    await user.click(screen.getByRole('button', { name: 'Registrar entrevista' }));

    expect(screen.getByRole('button', { name: 'Guardando...' })).toBeDisabled();
  });
});
