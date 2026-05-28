import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, postMock, setupUser, clearUser } from '../../test/test-utils';
import InspectorConvivenciaPage from './InspectorConvivenciaPage';

describe('InspectorConvivenciaPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setupUser(['DISCIPLINE_CREATE']);
    getMock.mockImplementation(async (path) => {
      if (path === '/api/inspector/incidentes/') {
        return { incidentes: [] };
      }
      if (path === '/api/inspector/estudiantes/') {
        return { estudiantes: [{ id: 7, nombre_completo: 'Ana Perez' }] };
      }
      if (path === '/api/v1/profesor/clases/') {
        return { results: [{ id: 5, nombre: 'Matematica 7A' }] };
      }
      if (path === '/api/inspector/justificativos/') {
        return { justificativos: [] };
      }
      return {};
    });
  });
  it('loads students on mount', async () => {
    renderWithProviders(<InspectorConvivenciaPage />);

    expect(screen.getByRole('status')).toBeInTheDocument();

    await screen.findAllByText('Ana Perez');
    expect(getMock).toHaveBeenCalledWith('/api/inspector/estudiantes/');
    expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/clases/');

    await waitFor(() => {
      expect(screen.getAllByText('Ana Perez').length).toBeGreaterThan(0);
    });
  });

  it('submits annotation when capability exists', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValueOnce({ message: 'Anotacion registrada.' });

    renderWithProviders(<InspectorConvivenciaPage />);

    // Wait for students to load before interacting with the select
    await screen.findAllByText('Ana Perez');

    const studentSelects = screen.getAllByLabelText('Estudiante');
    await user.selectOptions(studentSelects[0], '7');
    await user.type(screen.getByLabelText('Descripcion'), 'Conducta destacada');
    await user.click(screen.getByRole('button', { name: 'Registrar anotacion' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/inspector/anotaciones/crear/', {
        estudiante_id: 7,
        tipo: 'NEUTRA',
        categoria: 'OTRO',
        descripcion: 'Conducta destacada',
        gravedad: 1,
      });
    });
  });

  it('disables justificativo review action without capability', async () => {
    renderWithProviders(<InspectorConvivenciaPage />);

    const options = await screen.findAllByText('Ana Perez');
    expect(options.length).toBeGreaterThan(0);

    const submitButton = screen.getByRole('button', { name: 'Actualizar justificativo' });

    expect(submitButton).toBeDisabled();
    expect(postMock).not.toHaveBeenCalled();
  });
});
