import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders, paginated, getMock, postMock, patchMock, deleteMock , setupUser } from '../../test/test-utils';

import AdminAttendancePage from './AdminAttendancePage';

describe('AdminAttendancePage', () => {

  it('renders and loads initial data without interaction', async () => {
    getMock
      .mockResolvedValueOnce({ results: [{ id: 31, curso_nombre: '6A', asignatura_nombre: 'Historia' }] })
      .mockResolvedValue(paginated([]));

    setupUser(['CLASS_VIEW_ATTENDANCE', 'CLASS_TAKE_ATTENDANCE']);
    renderWithProviders(<AdminAttendancePage />, {
      route: '/admin/asistencias',
      path: '/admin/asistencias'
    });

    // Wait for classes to load
    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/clases/');
    }, { timeout: 5000 });

    // Just wait a moment for any effects to settle
    await waitFor(() => {
      expect(screen.getByTestId('admin-attendance-title')).toBeInTheDocument();
    }, { timeout: 5000 });
  });

  it('creates attendance with CLASS_TAKE_ATTENDANCE capability', async () => {
    const user = userEvent.setup();

    getMock
      .mockResolvedValueOnce({ results: [{ id: 31, curso_nombre: '6A', asignatura_nombre: 'Historia' }] })
      .mockResolvedValue(paginated([]));

    postMock.mockResolvedValue({ id_asistencia: 77 });

    setupUser(['CLASS_VIEW_ATTENDANCE', 'CLASS_TAKE_ATTENDANCE']);
    renderWithProviders(<AdminAttendancePage />, {
      route: '/admin/asistencias?clase_id=31',
      path: '/admin/asistencias'
    });

    // Wait for classes to load
    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/clases/');
    });

    // Wait for form to be ready
    await screen.findByLabelText('Estudiante ID');

    await user.type(screen.getByLabelText('Estudiante ID'), '44');
    await user.type(screen.getAllByLabelText('Fecha')[1], '2026-03-07');
    await user.click(screen.getByRole('button', { name: 'Crear' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/profesor/asistencias/', {
        clase: 31,
        estudiante: 44,
        fecha: '2026-03-07',
        estado: 'P',
        tipo_asistencia: null,
        observaciones: null,
      });
    });
  });

  it('updates and deletes attendance rows', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    getMock
      .mockResolvedValueOnce({ results: [{ id: 31, curso_nombre: '6A', asignatura_nombre: 'Historia' }] })
      .mockResolvedValue(
        paginated([
          {
            id_asistencia: 77,
            clase: 31,
            estudiante: 44,
            estudiante_nombre: 'Alumno Uno',
            fecha: '2026-03-07',
            estado: 'A',
            tipo_asistencia: 'Presencial',
            observaciones: 'Inicial',
          },
        ])
      );

    patchMock.mockResolvedValue({ id_asistencia: 77, estado: 'P' });
    deleteMock.mockResolvedValue(null);

    setupUser(['CLASS_VIEW_ATTENDANCE', 'CLASS_TAKE_ATTENDANCE']);
    renderWithProviders(<AdminAttendancePage />, {
      route: '/admin/asistencias?clase_id=31',
      path: '/admin/asistencias'
    });

    // Wait for data to render
    expect(await screen.findByText('Alumno Uno')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Editar' }));
    await user.selectOptions(screen.getByLabelText('Estado'), 'P');
    await user.click(screen.getByRole('button', { name: 'Actualizar' }));

    await waitFor(() => {
      expect(patchMock).toHaveBeenCalledWith('/api/v1/profesor/asistencias/77/', {
        clase: 31,
        estudiante: 44,
        fecha: '2026-03-07',
        estado: 'P',
        tipo_asistencia: 'Presencial',
        observaciones: 'Inicial',
      });
    });

    const deleteButtons = screen.getAllByRole('button', { name: 'Eliminar' });
    await user.click(deleteButtons[0]);

    await waitFor(() => {
      expect(deleteMock).toHaveBeenCalledWith('/api/v1/profesor/asistencias/77/');
    });
  });

  it('shows read-only mode without CLASS_TAKE_ATTENDANCE', async () => {
    getMock
      .mockResolvedValueOnce({ results: [{ id: 31, curso_nombre: '6A', asignatura_nombre: 'Historia' }] })
      .mockResolvedValue(paginated([]));

    setupUser(['CLASS_VIEW_ATTENDANCE']);
    renderWithProviders(<AdminAttendancePage />, {
      route: '/admin/asistencias?clase_id=31',
      path: '/admin/asistencias'
    });

    // Wait for the restricted mode message to render
    expect(await screen.findByText(/falta capability `CLASS_TAKE_ATTENDANCE`/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Crear' })).not.toBeInTheDocument();
  });

  it('keeps pagination controls aligned with the current page', async () => {
    getMock
      .mockResolvedValueOnce({ results: [{ id: 31, curso_nombre: '6A', asignatura_nombre: 'Historia' }] })
      .mockResolvedValue({
        count: 60,
        next: null,
        previous: null,
        results: [
          {
            id_asistencia: 88,
            clase: 31,
            estudiante: 55,
            estudiante_nombre: 'Alumno Dos',
            fecha: '2026-03-08',
            estado: 'P',
            tipo_asistencia: 'Presencial',
            observaciones: '',
          },
        ],
      });

    setupUser(['CLASS_VIEW_ATTENDANCE', 'CLASS_TAKE_ATTENDANCE']);
    renderWithProviders(<AdminAttendancePage />, {
      route: '/admin/asistencias?clase_id=31&page=2',
      path: '/admin/asistencias'
    });

    expect(await screen.findByText('Pagina 2 de 2 (Total: 60)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Anterior' })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled();
  });
});
