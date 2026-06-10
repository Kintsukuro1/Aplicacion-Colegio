import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, beforeEach } from 'vitest';
import { renderWithProviders, getMock } from '../../test/test-utils';

import TeacherClassesPage from './TeacherClassesPage';

describe('TeacherClassesPage', () => {
  beforeEach(() => {
    getMock.mockImplementation(async (path) => {
      if (path === '/api/v1/profesor/clases/') {
        return {
          results: [
            {
              id: 1,
              curso_nombre: '7° Básico A',
              asignatura_nombre: 'Matemática',
              total_estudiantes: 28,
              activo: true,
            },
            {
              id: 2,
              curso_nombre: '7° Básico B',
              asignatura_nombre: 'Lenguaje',
              total_estudiantes: 30,
              activo: false,
            },
          ],
        };
      }

      // Handle tendencias with query parameters (flexible matching)
      if (path.includes('/api/v1/profesor/tendencias/')) {
        return {
          tendencia_general: {
            promedio_general: 5.9,
            porcentaje_asistencia: 94.1,
            total_clases: 2,
          },
          asistencia_mensual: [
            { mes: 'Mar', porcentaje: 93, total_registros: 20 },
            { mes: 'Abr', porcentaje: 95, total_registros: 18 },
          ],
          tendencias_por_clase: [
            {
              clase_id: 1,
              curso: '7° Básico A',
              asignatura: 'Matemática',
              promedio_actual: 6.1,
              promedio_anterior: 5.8,
              tendencia: 'sube',
              porcentaje_aprobacion: 96,
              porcentaje_asistencia: 95,
            },
          ],
        };
      }

      if (path === '/api/v1/profesor/mi-horario/') {
        return {
          total_bloques: 4,
          horario: {
            Lunes: [
              {
                id: 11,
                bloque_numero: 1,
                hora_inicio: '08:00',
                hora_fin: '08:45',
                curso_nombre: '7° Básico A',
                asignatura_nombre: 'Matemática',
              },
            ],
            Martes: [],
          },
        };
      }

      return null;
    });
  });

  it('renders summaries, schedule and class trends from API data', async () => {
    const user = userEvent.setup({ delay: null });
    renderWithProviders(<TeacherClassesPage />);

    // Wait for data to load and summaries to render
    await waitFor(() => {
      expect(screen.getByText('Clases cargadas')).toBeInTheDocument();
    });

    expect(screen.getByText('Clases cargadas').closest('.summary-tile')).toHaveTextContent('2');
    expect(screen.getAllByText('7° Básico A').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Matemática').length).toBeGreaterThan(0);
    expect(screen.getByText('Tendencias del Profesor')).toBeInTheDocument();
    expect(screen.getByText('Mi Horario Semanal')).toBeInTheDocument();
    expect(screen.getByText('Bloque 1')).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Periodo'), 'anual');

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/profesor/tendencias/?periodo=anual');
    });
  });

  it('shows a loading state while classes are being fetched', () => {
    getMock.mockImplementation(() => new Promise(() => {}));

    renderWithProviders(<TeacherClassesPage />);

    // Summary skeletons should be visible during loading
    const skeletons = document.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons.length).toBeGreaterThan(0);
    
    // Page title should always be visible
    expect(screen.getByTestId('teacher-classes-title')).toBeInTheDocument();
  });
});