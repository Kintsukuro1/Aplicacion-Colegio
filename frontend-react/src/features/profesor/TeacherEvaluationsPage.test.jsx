import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { renderWithProviders, getMock, setupUser, clearUser } from '../../test/test-utils';
import TeacherEvaluationsPage from './TeacherEvaluationsPage';

describe('TeacherEvaluationsPage', () => {
  beforeEach(() => {
    setupUser(['GRADE_CREATE', 'GRADE_EDIT', 'GRADE_DELETE']);

    getMock.mockImplementation(async (path) => {
      if (path === '/api/v1/profesor/clases/') {
        return {
          results: [
            { id: 1, curso_nombre: '7° Básico A', asignatura_nombre: 'Matemática' },
            { id: 2, curso_nombre: '7° Básico B', asignatura_nombre: 'Lenguaje' },
          ],
        };
      }

      if (path === '/api/v1/profesor/evaluaciones/?clase_id=1') {
        return {
          results: [
            {
              id_evaluacion: 11,
              nombre: 'Prueba parcial',
              fecha_evaluacion: '2026-04-10',
              ponderacion: 60,
              tipo_evaluacion: 'sumativa',
              clase: 1,
            },
            {
              id_evaluacion: 12,
              nombre: 'Tarea grupal',
              fecha_evaluacion: '2026-04-17',
              ponderacion: 40,
              tipo_evaluacion: 'formativa',
              clase: 1,
            },
          ],
        };
      }

      if (path === '/api/v1/profesor/evaluaciones/?clase_id=2') {
        return { results: [] };
      }

      return { results: [] };
    });
  });
  it('renders summaries and evaluations, then reloads when class changes', async () => {
    const user = userEvent.setup();

    renderWithProviders(<TeacherEvaluationsPage />);

    await waitFor(() => {
      expect(screen.getByTestId('teacher-evaluations-title')).toBeInTheDocument();
    });

    expect(screen.queryByText('Modo restringido: falta capability `GRADE_CREATE` para crear.')).not.toBeInTheDocument();
    expect(screen.getByText('+ Nueva Evaluación')).toBeInTheDocument();
    expect(screen.getByText('Listado de Evaluaciones')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Evaluaciones')).toBeInTheDocument();
      expect(screen.getByText('Prueba parcial')).toBeInTheDocument();
      expect(screen.getByText('Tarea grupal')).toBeInTheDocument();
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/evaluaciones/?clase_id=1');
    });

    await user.selectOptions(screen.getByLabelText('Clase'), '2');

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/evaluaciones/?clase_id=2');
    });
  });

  it('shows a loading state before evaluations are fetched', () => {
    getMock.mockImplementation(() => new Promise(() => {}));

    renderWithProviders(<TeacherEvaluationsPage />);

    // Table loading state should be visible
    expect(screen.getByRole('status')).toBeInTheDocument();
    
    // Section header should always be visible
    expect(screen.getByText('Listado de Evaluaciones')).toBeInTheDocument();
  });
});