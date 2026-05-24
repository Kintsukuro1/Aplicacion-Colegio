import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { renderWithProviders, getMock } from '../../test/test-utils';
import { useAuthStore } from '../../lib/store/useAuthStore';

import TeacherGradesPage from './TeacherGradesPage';

describe('TeacherGradesPage', () => {
  beforeEach(() => {
    useAuthStore.getState().setUser({ capabilities: ['GRADE_CREATE', 'GRADE_EDIT', 'GRADE_DELETE'] });

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

      if (path === '/api/v1/profesor/evaluaciones/?clase_id=1') {
        return {
          results: [
            { id_evaluacion: 11, nombre: 'Parcial 1', fecha_evaluacion: '2026-04-10', clase: 1 },
            { id_evaluacion: 12, nombre: 'Trabajo 1', fecha_evaluacion: '2026-04-17', clase: 1 },
          ],
        };
      }

      if (path === '/api/v1/profesor/evaluaciones/?clase_id=2') {
        return {
          results: [
            { id_evaluacion: 21, nombre: 'Parcial 2', fecha_evaluacion: '2026-04-20', clase: 2 },
          ],
        };
      }

      if (path === '/api/v1/profesor/calificaciones/?clase_id=1') {
        return {
          results: [
            { id_calificacion: 1, evaluacion: 11, evaluacion_nombre: 'Parcial 1', estudiante: 101, estudiante_nombre: 'Ana Lagos', nota: 6.5, fecha_creacion: '2026-04-12T09:00:00-04:00' },
            { id_calificacion: 2, evaluacion: 11, evaluacion_nombre: 'Parcial 1', estudiante: 102, estudiante_nombre: 'Bruno Paz', nota: 5.0, fecha_creacion: '2026-04-12T09:00:00-04:00' },
            { id_calificacion: 4, evaluacion: 12, evaluacion_nombre: 'Trabajo 1', estudiante: 101, estudiante_nombre: 'Ana Lagos', nota: 6.0, fecha_creacion: '2026-04-18T09:00:00-04:00' },
          ],
        };
      }

      if (path === '/api/v1/profesor/calificaciones/?evaluacion_id=11') {
        return {
          next: 'http://127.0.0.1:8000/api/v1/profesor/calificaciones/?evaluacion_id=11&cursor=page2',
          results: [
            { id_calificacion: 1, evaluacion: 11, evaluacion_nombre: 'Parcial 1', estudiante: 101, estudiante_nombre: 'Ana Lagos', nota: 6.5, fecha_creacion: '2026-04-12T09:00:00-04:00' },
            { id_calificacion: 2, evaluacion: 11, evaluacion_nombre: 'Parcial 1', estudiante: 102, estudiante_nombre: 'Bruno Paz', nota: 5.0, fecha_creacion: '2026-04-12T09:00:00-04:00' },
          ],
        };
      }

      if (path === '/api/v1/profesor/calificaciones/?evaluacion_id=11&cursor=page2') {
        return {
          next: null,
          results: [
            { id_calificacion: 5, evaluacion: 11, evaluacion_nombre: 'Parcial 1', estudiante: 103, estudiante_nombre: 'Camila Campos', nota: 6.2, fecha_creacion: '2026-04-12T09:00:00-04:00' },
          ],
        };
      }

      if (path === '/api/v1/profesor/calificaciones/?evaluacion_id=12') {
        return {
          results: [
            { id_calificacion: 4, evaluacion: 12, evaluacion_nombre: 'Trabajo 1', estudiante: 101, estudiante_nombre: 'Ana Lagos', nota: 6.0, fecha_creacion: '2026-04-18T09:00:00-04:00' },
          ],
        };
      }

      if (path === '/api/v1/profesor/calificaciones/?clase_id=2') {
        return {
          results: [
            { id_calificacion: 3, evaluacion: 21, evaluacion_nombre: 'Parcial 2', estudiante: 101, estudiante_nombre: 'Ana Lagos', nota: 7.0, fecha_creacion: '2026-04-21T09:00:00-04:00' },
          ],
        };
      }

      if (path === '/api/v1/profesor/calificaciones/?evaluacion_id=21') {
        return {
          results: [
            { id_calificacion: 3, evaluacion: 21, evaluacion_nombre: 'Parcial 2', estudiante: 101, estudiante_nombre: 'Ana Lagos', nota: 7.0, fecha_creacion: '2026-04-21T09:00:00-04:00' },
          ],
        };
      }

      return { results: [] };
    });
  });

  afterEach(() => {
    useAuthStore.getState().setUser(null);
  });

  it('renders summaries and reloads grades when the class filter changes', async () => {
    const user = userEvent.setup();

    renderWithProviders(<TeacherGradesPage />);

    await waitFor(() => {
      expect(screen.getByText('Profesor: Calificaciones')).toBeInTheDocument();
      expect(screen.getByText('Listado de Calificaciones')).toBeInTheDocument();
      expect(screen.getByText('Calificaciones')).toBeInTheDocument();
      expect(screen.getByText('Promedio')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('Vista agrupada por estudiante con todas las evaluaciones de la clase.')).toBeInTheDocument();
      expect(screen.getByText('Nota 2')).toBeInTheDocument();
      expect(screen.getAllByText('Ana Lagos').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Bruno Paz').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Camila Campos')).toBeInTheDocument();
      expect(screen.getAllByText('Parcial 1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Trabajo 1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('18/04')).toBeInTheDocument();
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/calificaciones/?evaluacion_id=11');
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/calificaciones/?evaluacion_id=11&cursor=page2');
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/calificaciones/?evaluacion_id=12');
    });

    expect(screen.getByRole('button', { name: 'Todas' })).toHaveAttribute('aria-pressed', 'true');

    await user.click(screen.getByRole('button', { name: /Parcial 1/ }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Parcial 1/ })).toHaveAttribute('aria-pressed', 'true');
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/calificaciones/?evaluacion_id=11');
    });

    await user.selectOptions(screen.getByLabelText('Clase'), '2');

    await waitFor(() => {
      expect(screen.getAllByText('7,0').length).toBeGreaterThanOrEqual(2);
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/calificaciones/?evaluacion_id=21');
    });
  });
});
