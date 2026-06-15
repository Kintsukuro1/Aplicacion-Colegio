import { act, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderWithProviders, getMock, createDeferred } from '../../test/test-utils';

import StudentSelfPage from './StudentSelfPage';





describe('StudentSelfPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders a structured student overview from API data', async () => {
    const historyDeferred = createDeferred();

    getMock.mockImplementation(async (path) => {
      if (path === '/api/v1/estudiante/mi-perfil/') {
        return {
          nombre_completo: 'Valentina Rojas',
          email: 'valentina@test.cl',
          rut: '12345678-9',
          curso_actual: '7° Básico A',
          colegio: 'Colegio Demo',
        };
      }

      if (path === '/api/v1/estudiante/mis-clases/') {
        return [
          { clase_id: 1, asignatura: 'Matemática', curso: '7° Básico A' },
          { clase_id: 2, asignatura: 'Lenguaje', curso: '7° Básico A' },
        ];
      }

      if (path === '/api/v1/estudiante/mis-notas/') {
        return [
          { id: 1, evaluacion: 'Prueba 1', curso: '7° Básico A', nota: 6.2 },
          { id: 2, evaluacion: 'Tarea 2', curso: '7° Básico A', nota: 5.8 },
        ];
      }

      if (path === '/api/v1/estudiante/mi-asistencia/') {
        return [
          { id: 1, fecha: '2026-04-01', estado: 'Presente' },
          { id: 2, fecha: '2026-04-02', estado: 'Ausente' },
        ];
      }

      if (path.includes('/api/v1/estudiante/historial-academico/')) {
        return historyDeferred.promise;
      }

      throw new Error(`Unexpected endpoint: ${path}`);
    });

    const { unmount } = renderWithProviders(<StudentSelfPage />);

    await waitFor(() => {
      expect(screen.getByText('Estudiante: Mi Panel')).toBeInTheDocument();
      expect(screen.getByText('Valentina Rojas')).toBeInTheDocument();
    });

    unmount();

    renderWithProviders(<StudentSelfPage />, {
      route: '/estudiante/historial',
      path: '/estudiante/historial',
    });

    await waitFor(() => {
      expect(screen.getByText('Cargando historial')).toBeInTheDocument();
    });

    await act(async () => {
      historyDeferred.resolve({
        ciclo: { id: 2026, nombre: '2026', estado: 'Activo' },
        ciclos_disponibles: [{ id: 2026, nombre: '2026', estado: 'Activo' }],
        asignaturas: [
          { clase_id: 1, asignatura: 'Matemática', curso: '7° Básico A', promedio: 6.2, porcentaje_asistencia: 95, notas: [6.0, 6.4] },
          { clase_id: 2, asignatura: 'Lenguaje', curso: '7° Básico A', promedio: 5.8, porcentaje_asistencia: 92, notas: [5.5, 6.1] },
        ],
      });
    });

    await waitFor(() => {
      expect(screen.getByText('2026')).toBeInTheDocument();
      expect(screen.getAllByText('Matemática').length).toBeGreaterThan(0);
    });
  });
});