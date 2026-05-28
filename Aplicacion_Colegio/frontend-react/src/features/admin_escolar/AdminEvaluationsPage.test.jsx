import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, patchMock, postMock, paginated, setupUser, clearUser, createDeferred } from '../../test/test-utils';
import AdminEvaluationsPage from './AdminEvaluationsPage';

describe('AdminEvaluationsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setupUser(['GRADE_EDIT']);
  });
  it('renders with deferred loading and displays evaluations', async () => {
    const listDeferred = createDeferred();

    getMock.mockImplementation((url) => {
      if (url.includes('/api/v1/evaluaciones/')) {
        return listDeferred.promise;
      }
      return {};
    });

    renderWithProviders(<AdminEvaluationsPage />);

    // Verify title and loading state
    expect(screen.getByTestId('admin-evaluations-title')).toBeInTheDocument();

    // While loading, skeletons show
    const skeletons = screen.getAllByRole('status');
    expect(skeletons.length).toBeGreaterThan(0);

    // Resolve API response
    await act(async () => {
      listDeferred.resolve(
        paginated([
          { id_evaluacion: 10, nombre: 'Prueba Parcial', clase: 'Lenguaje 5A', tipo_evaluacion: 'PRUEBA', activa: true, ponderacion: 20 },
        ])
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Prueba Parcial')).toBeInTheDocument();
      expect(screen.getByText('Lenguaje 5A')).toBeInTheDocument();
    });
  });

  it('allows bulk toggling active status if GRADE_EDIT is present', async () => {
    const user = userEvent.setup({ delay: null });

    getMock.mockResolvedValue(
      paginated([
        { id_evaluacion: 10, nombre: 'Prueba Parcial', clase: 'Lenguaje 5A', tipo_evaluacion: 'PRUEBA', activa: true, ponderacion: 20 },
      ])
    );

    // Mock the bulk toggle endpoint (falls back to individual PATCH)
    patchMock.mockResolvedValue({ id_evaluacion: 10, activa: false });
    postMock.mockRejectedValue({ status: 404 }); // bulk endpoint not available

    renderWithProviders(<AdminEvaluationsPage />);

    await screen.findByText('Prueba Parcial');

    // Select the evaluation checkbox (first checkbox in the body row)
    const checkboxes = screen.getAllByRole('checkbox');
    // First checkbox is select-all, second is the row checkbox
    await user.click(checkboxes[1]);

    // Click the "Desactivar Seleccionadas" button
    window.confirm = vi.fn(() => true);
    const deactivateButton = screen.getByRole('button', { name: /Desactivar Seleccionadas/i });
    await user.click(deactivateButton);

    await waitFor(() => {
      expect(patchMock).toHaveBeenCalledWith('/api/v1/profesor/evaluaciones/10/', { activa: false });
    });
  });
});
