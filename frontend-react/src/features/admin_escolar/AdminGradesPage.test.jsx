import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders, paginated, getMock, postMock, patchMock, deleteMock , setupUser } from '../../test/test-utils';

import AdminGradesPage from './AdminGradesPage';

describe('AdminGradesPage', () => {

  it('creates grade with GRADE_CREATE capability', async () => {
    const user = userEvent.setup();

    getMock.mockResolvedValue(paginated([]));
    postMock.mockResolvedValue({ id_calificacion: 55 });

    setupUser(['GRADE_VIEW', 'GRADE_CREATE']);
    renderWithProviders(<AdminGradesPage />, {
      route: '/admin/calificaciones',
      path: '/admin/calificaciones'
    });

    // Wait for data to load
    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/profesor/calificaciones/'));
    });

    // Wait for loading to finish
    await screen.findByText('Evaluacion ID');
    await user.type(screen.getByLabelText('Evaluacion ID'), '10');
    await user.type(screen.getByLabelText('Estudiante ID'), '21');
    await user.type(screen.getByLabelText('Nota'), '6.2');
    await user.click(screen.getByRole('button', { name: 'Crear' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/profesor/calificaciones/', {
        evaluacion: 10,
        estudiante: 21,
        nota: 6.2,
      });
    });
  });

  it('updates grade with GRADE_EDIT capability', async () => {
    const user = userEvent.setup();

    getMock.mockResolvedValue(
      paginated([
        {
          id_calificacion: 55,
          evaluacion: 10,
          estudiante: 21,
          estudiante_nombre: 'Alumno Test',
          nota: 5.8,
        },
      ])
    );

    patchMock.mockResolvedValue({ id_calificacion: 55, nota: 6.0 });

    setupUser(['GRADE_VIEW', 'GRADE_EDIT']);
    renderWithProviders(<AdminGradesPage />, {
      route: '/admin/calificaciones',
      path: '/admin/calificaciones'
    });

    // Wait for table data to render
    expect(await screen.findByText('Alumno Test')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Editar' }));

    const scoreInput = screen.getByLabelText('Nota');
    await user.clear(scoreInput);
    await user.type(scoreInput, '6.0');
    await user.click(screen.getByRole('button', { name: 'Actualizar' }));

    await waitFor(() => {
      expect(patchMock).toHaveBeenCalledWith('/api/v1/profesor/calificaciones/55/', {
        evaluacion: 10,
        estudiante: 21,
        nota: 6,
      });
    });
  });

  it('deletes grade with GRADE_DELETE capability', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    getMock.mockResolvedValue(
      paginated([
        {
          id_calificacion: 55,
          evaluacion: 10,
          estudiante: 21,
          estudiante_nombre: 'Alumno Test',
          nota: 5.8,
        },
      ])
    );

    deleteMock.mockResolvedValue(null);

    setupUser(['GRADE_VIEW', 'GRADE_DELETE']);
    renderWithProviders(<AdminGradesPage />, {
      route: '/admin/calificaciones',
      path: '/admin/calificaciones'
    });

    // Wait for table data to render
    expect(await screen.findByText('Alumno Test')).toBeInTheDocument();

    const deleteButtons = screen.getAllByRole('button', { name: 'Eliminar' });
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(deleteMock).toHaveBeenCalledWith('/api/v1/profesor/calificaciones/55/');
    });
  });

  it('read-only user sees restrictions', async () => {
    getMock.mockResolvedValue(paginated([]));

    setupUser(['GRADE_VIEW']);
    renderWithProviders(<AdminGradesPage />, {
      route: '/admin/calificaciones',
      path: '/admin/calificaciones'
    });

    // Wait for data to load and table to render
    expect(await screen.findByText(/falta capability `GRADE_CREATE` para crear/)).toBeInTheDocument();
    expect(screen.getByText(/falta capability `GRADE_DELETE` para eliminacion masiva/)).toBeInTheDocument();
  });
});
