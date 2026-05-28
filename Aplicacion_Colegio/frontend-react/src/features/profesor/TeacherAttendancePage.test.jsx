import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, beforeEach } from 'vitest';
import { renderWithProviders, getMock, setupUser, clearUser } from '../../test/test-utils';
import TeacherAttendancePage from './TeacherAttendancePage';

describe('TeacherAttendancePage', () => {
  beforeEach(() => {
    setupUser(['CLASS_TAKE_ATTENDANCE']);

    getMock.mockImplementation(async (path) => {
      if (path === '/api/v1/profesor/clases/') {
        return {
          results: [
            { id: 1, curso_nombre: '7° Básico A', asignatura_nombre: 'Matemática' },
            { id: 2, curso_nombre: '7° Básico B', asignatura_nombre: 'Lenguaje' },
          ],
        };
      }

      if (path === '/api/v1/estudiantes/') {
        return {
          results: [
            { id: 101, nombre: 'Ana', apellido_paterno: 'Lagos' },
            { id: 102, nombre: 'Bruno', apellido_paterno: 'Paz' },
          ],
        };
      }

      if (path === '/api/v1/profesor/asistencias/?clase_id=1') {
        return {
          results: [
            {
              id_asistencia: 1,
              fecha: '2026-04-10',
              estudiante_nombre: 'Ana Lagos',
              estado: 'P',
              tipo_asistencia: 'Presencial',
              clase: 1,
              estudiante: 101,
            },
            {
              id_asistencia: 2,
              fecha: '2026-04-10',
              estudiante_nombre: 'Bruno Paz',
              estado: 'A',
              tipo_asistencia: 'Presencial',
              clase: 1,
              estudiante: 102,
            },
          ],
        };
      }

      if (path === '/api/v1/profesor/asistencias/?clase_id=2') {
        return {
          results: [
            {
              id_asistencia: 3,
              fecha: '2026-04-11',
              estudiante_nombre: 'Ana Lagos',
              estado: 'T',
              tipo_asistencia: 'Remota',
              clase: 2,
              estudiante: 101,
            },
          ],
        };
      }

      return { results: [] };
    });
  });
  it('renders summaries and reloads attendance when class changes', async () => {
    const user = userEvent.setup();

    renderWithProviders(<TeacherAttendancePage />);

    await waitFor(() => {
      expect(screen.getByText('Profesor: Asistencias')).toBeInTheDocument();
      expect(screen.getByText('Listado de Asistencias')).toBeInTheDocument();
      expect(screen.getByText('Registros')).toBeInTheDocument();
      expect(screen.getByText('Presentes')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getAllByText('Ana Lagos').length).toBeGreaterThanOrEqual(2);
      expect(screen.getAllByText('Bruno Paz').length).toBeGreaterThanOrEqual(2);
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/asistencias/?clase_id=1');
    });

    await user.selectOptions(screen.getByLabelText('Clase'), '2');

    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('Tardanzas')).toBeInTheDocument();
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/asistencias/?clase_id=2');
    });
  });

  it('shows a loading state before attendance data is ready', () => {
    getMock.mockImplementation(() => new Promise(() => {}));

    renderWithProviders(<TeacherAttendancePage />);

    // Section header should always be visible
    expect(screen.getByText('Listado de Asistencias')).toBeInTheDocument();
    
    // Summary skeletons should be visible
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});