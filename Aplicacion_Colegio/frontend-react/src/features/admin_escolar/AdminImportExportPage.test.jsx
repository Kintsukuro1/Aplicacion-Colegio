import { screen, waitFor, act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, setupUser, clearUser, createDeferred } from '../../test/test-utils';
import AdminImportExportPage from './AdminImportExportPage';

describe('AdminImportExportPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setupUser(['SYSTEM_ADMIN']);
  });
  it('renders deferred loading and dashboard data', async () => {
    const dashboardDeferred = createDeferred();

    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/importacion/dashboard/')) {
        return dashboardDeferred.promise;
      }
      if (url.includes('/api/v1/profesor/clases/')) {
        return { results: [] };
      }
      return {};
    });

    const { container } = renderWithProviders(<AdminImportExportPage />);

    // Page title and section titles are immediately visible
    expect(screen.getByText('Admin Escolar: Importacion y Exportacion')).toBeInTheDocument();
    
    // Skeleton should be shown
    expect(container.querySelectorAll('.summary-skeleton').length).toBeGreaterThan(0);

    // Resolve API data
    await act(async () => {
      dashboardDeferred.resolve({
        total_estudiantes: 450,
        total_profesores: 30,
        total_apoderados: 120,
      });
    });

    await waitFor(() => {
      expect(screen.getByText('Estudiantes')).toBeInTheDocument();
      expect(screen.getByText('450')).toBeInTheDocument();
      expect(screen.getByText('Profesores')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
    });
  });

  it('shows read-only permissions notice for configuration-only users', () => {
    setupUser(['SYSTEM_CONFIGURE']);

    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/importacion/dashboard/')) {
        return Promise.resolve({ total_estudiantes: 1, total_profesores: 2, total_apoderados: 3 });
      }
      if (url.includes('/api/v1/profesor/clases/')) {
        return Promise.resolve({ results: [] });
      }
      return Promise.resolve({});
    });

    renderWithProviders(<AdminImportExportPage />);

    expect(screen.getByRole('status')).toHaveTextContent('Vista de consulta');
    expect(screen.getByText(/Tu rol puede ver el resumen del colegio/)).toBeInTheDocument();
    expect(screen.getByText('Las exportaciones masivas requieren rol de administrador del sistema.')).toBeInTheDocument();
  });
});
