import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock } from '../../test/test-utils';

import AsesorFinancieroPage from './AsesorFinancieroPage';

describe('AsesorFinancieroPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    getMock.mockImplementation(async (path) => {
      if (path.startsWith('/api/v1/finanzas/dashboard/')) {
        return {
          resumen: {
            total_emitido: 1250000,
            total_pagado: 850000,
            total_pendiente: 400000,
            tasa_cobranza: 68,
          },
          morosidad: {
            familias_morosas: 3,
            monto_vencido: 275000,
          },
          cuotas_por_estado: [
            { estado: 'Pagada', cantidad: 12, monto: 850000 },
            { estado: 'Pendiente', cantidad: 4, monto: 400000 },
          ],
          becas: {
            vigentes: 2,
            por_tipo: [{ tipo: 'Socioeconómica', total: 2 }],
          },
          pagos_recientes: [
            { id: 1, estudiante: 'Ana Lagos', monto: 125000, estado: 'Pagado' },
            { id: 2, estudiante: 'Bruno Paz', monto: 95000, estado: 'Pagado' },
          ],
        };
      }

      if (path === '/api/v1/finanzas/morosos/') {
        return {
          morosos: [
            { estudiante_id: 1, nombre: 'Ana Lagos', cuotas_vencidas: 2, monto_total_adeudado: 120000 },
            { estudiante_id: 2, nombre: 'Bruno Paz', cuotas_vencidas: 1, monto_total_adeudado: 95000 },
          ],
        };
      }

      return {};
    });
  });

  it('renders financial summaries and reloads when filters change', async () => {
    const user = userEvent.setup();

    renderWithProviders(<AsesorFinancieroPage />);

    await waitFor(() => {
      expect(screen.getByTestId('asesor-financiero-title')).toBeInTheDocument();
      expect(screen.getByText('Resumen Financiero')).toBeInTheDocument();
      expect(screen.getByText('Morosidad')).toBeInTheDocument();
      expect(screen.getByText('Pagos recientes')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('$1.250.000')).toBeInTheDocument();
      expect(screen.getByText('$850.000')).toBeInTheDocument();
      expect(screen.getByText('$400.000')).toBeInTheDocument();
      expect(screen.getByText('68%')).toBeInTheDocument();
      expect(getMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/finanzas/dashboard/?anio='));
    });

    await user.selectOptions(screen.getByLabelText('Mes'), '4');

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith(expect.stringContaining('mes=4'));
    });
  });
});