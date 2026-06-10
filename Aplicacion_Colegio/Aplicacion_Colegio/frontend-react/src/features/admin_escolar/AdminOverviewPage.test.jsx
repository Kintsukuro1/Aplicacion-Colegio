import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, postMock, createDeferred } from '../../test/test-utils';

import AdminOverviewPage from './AdminOverviewPage';



describe('AdminOverviewPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders summary metrics with loading skeletons using deferred promises', async () => {
    const overviewDeferred = createDeferred();
    const cyclesDeferred = createDeferred();

    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/dashboard/resumen/')) {
        return overviewDeferred.promise;
      }
      if (url.includes('/api/v1/ciclos-academicos/')) {
        return cyclesDeferred.promise;
      }
      return {};
    });

    const { container } = renderWithProviders(<AdminOverviewPage />);

    // Verify loading state
    expect(screen.getByTestId('admin-overview-title')).toBeInTheDocument();
    expect(container.querySelectorAll('.summary-skeleton').length).toBeGreaterThan(0);

    // Resolve promise
    await act(async () => {
      overviewDeferred.resolve({
        sections: {
          school: {
            students: 1250,
            teachers: 80,
            courses_active: 12,
            classes_active: 45,
            attendance_today: 90,
            evaluations_upcoming: 7,
          },
        },
      });
      cyclesDeferred.resolve({
        results: [{ id: 1, nombre: '2026', estado: 'ACTIVO' }],
      });
    });

    // Verify loaded content
    await waitFor(() => {
      expect(screen.getByText('Estudiantes')).toBeInTheDocument();
      expect(screen.getByText('1250')).toBeInTheDocument();
      expect(screen.getByText('Profesores')).toBeInTheDocument();
      expect(screen.getByText('80')).toBeInTheDocument();
    });
  });

  it('handles cycle transition request', async () => {
    const user = userEvent.setup();
    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/dashboard/resumen/')) {
        return Promise.resolve({
          sections: { school: { students: 0, teachers: 0, courses_active: 0, classes_active: 0, attendance_today: 0, evaluations_upcoming: 0 } },
        });
      }
      if (url.includes('/api/v1/ciclos-academicos/') && url.includes('/estadisticas/')) {
        return Promise.resolve({
          ciclo: { estado: 'ACTIVO' },
          matriculas: { total: 120 },
          academico: { cursos: 10, promedio_general: 6.1, porcentaje_asistencia: 92 },
          financiero: { tasa_cobranza: 85 },
        });
      }
      if (url.includes('/api/v1/ciclos-academicos/')) {
        return Promise.resolve({ results: [{ id: 1, nombre: '2026', estado: 'ACTIVO' }] });
      }
      return Promise.resolve({});
    });
    postMock.mockResolvedValue({ estado_anterior: 'PLANIFICACION', estado_actual: 'ACTIVO', warnings: [] });

    renderWithProviders(<AdminOverviewPage />);

    const select = await screen.findByLabelText('Ciclo');
    await user.selectOptions(select, '1');

    const activateBtn = screen.getByRole('button', { name: 'ACTIVO' });
    await user.click(activateBtn);

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/ciclos-academicos/1/transicion/', { nuevo_estado: 'ACTIVO' });
      expect(screen.getByText('Transicion aplicada: PLANIFICACION -> ACTIVO')).toBeInTheDocument();
    });
  });
});
