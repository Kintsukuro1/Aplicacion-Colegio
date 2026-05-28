import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, postMock, patchMock, deleteMock, setupUser, clearUser } from '../../test/test-utils';
import CalendarEventsPage from './CalendarEventsPage';

describe('CalendarEventsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setupUser(['ANNOUNCEMENT_VIEW', 'ANNOUNCEMENT_CREATE']);

    getMock.mockImplementation(async (path) => {
      if (path === '/api/v1/calendario/?page=1') {
        return {
          count: 2,
          next: null,
          previous: null,
          results: [
            {
              id_evento: 1,
              titulo: 'Reunión de apoderados',
              tipo: 'reunion',
              tipo_display: 'Reunión',
              fecha_inicio: '2026-04-10',
              fecha_fin: '2026-04-10',
              visibilidad: 'apoderados',
              color: '#3B82F6',
            },
            {
              id_evento: 2,
              titulo: 'Evaluación interna',
              tipo: 'evaluacion',
              tipo_display: 'Evaluación',
              fecha_inicio: '2026-04-15',
              fecha_fin: '2026-04-15',
              visibilidad: 'profesores',
              color: '#10B981',
            },
          ],
        };
      }

      if (path === '/api/v1/calendario/?page=1&tipo=reunion&mes=4') {
        return {
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id_evento: 1,
              titulo: 'Reunión de apoderados',
              tipo: 'reunion',
              tipo_display: 'Reunión',
              fecha_inicio: '2026-04-10',
              fecha_fin: '2026-04-10',
              visibilidad: 'apoderados',
              color: '#3B82F6',
            },
          ],
        };
      }

      return {
        count: 0,
        next: null,
        previous: null,
        results: []
      };
    });
  });
  it('renders summary cards and reloads when filters are applied', async () => {
    const user = userEvent.setup({ delay: null });

    renderWithProviders(<CalendarEventsPage />);

    // Wait for data to load and summaries to render
    await waitFor(() => {
      expect(screen.getByTestId('calendar-events-title')).toBeInTheDocument();
      expect(screen.getByText('Eventos visibles')).toBeInTheDocument();
      expect(screen.getByText('Filtros activos')).toBeInTheDocument();
    });

    // Switch to list view to see event text (grid view filters by current month)
    await user.click(screen.getByRole('button', { name: 'Vista Lista' }));

    await waitFor(() => {
      expect(screen.getByText('Reunión de apoderados')).toBeInTheDocument();
      expect(screen.getByText('Evaluación interna')).toBeInTheDocument();
    });

    const tipoSelects = screen.getAllByLabelText('Tipo');
    await user.selectOptions(tipoSelects[0], 'reunion');
    await user.clear(screen.getByLabelText('Mes'));
    await user.type(screen.getByLabelText('Mes'), '4');
    await user.click(screen.getByRole('button', { name: 'Aplicar Filtros' }));

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith(expect.stringContaining('tipo=reunion'));
      expect(screen.getAllByText('Reunión de apoderados').length).toBeGreaterThanOrEqual(1);
    });
  });
});