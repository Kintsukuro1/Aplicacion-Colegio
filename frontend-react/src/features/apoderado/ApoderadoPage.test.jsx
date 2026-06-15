import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, postMock } from '../../test/test-utils';

import ApoderadoPage from './ApoderadoPage';

describe('ApoderadoPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    getMock.mockImplementation((path) => {
      if (path === '/api/v1/apoderado/justificativos/') {
        return Promise.resolve({ justificativos: [{ id_justificativo: 2, fecha_ausencia: '2026-03-01', estado: 'PENDIENTE' }] });
      }
      if (path === '/api/v1/apoderado/firmas/') {
        return Promise.resolve({ pendientes: [{ id: 10 }], firmados: [{ id: 20 }] });
      }
      if (path === '/api/v1/apoderado/admision/opciones/') {
        return Promise.resolve({ cursos: [{ id: 1, nombre: '1° Básico' }], ciclos: [{ id: 2, nombre: '2026' }] });
      }
      return Promise.resolve({});
    });
  });

  it('loads justificativos and firmas counters', async () => {
    renderWithProviders(<ApoderadoPage />);

    // Wait for the GET calls to be made
    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/apoderado/justificativos/');
      expect(getMock).toHaveBeenCalledWith('/api/v1/apoderado/firmas/');
    });

    // Wait for the data to be rendered
    expect(await screen.findByText(/Justificativos \(1\)/)).toBeInTheDocument();
    expect(screen.getByText('Pendientes: 1')).toBeInTheDocument();
    expect(screen.getByText('Firmados: 1')).toBeInTheDocument();
    expect(screen.getByText('Pendientes de firma')).toBeInTheDocument();
  });

  it('submits sign document form', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValueOnce({ message: 'Documento firmado correctamente.' });

    renderWithProviders(<ApoderadoPage />);

    await screen.findByText(/Justificativos \(1\)/);

    await user.type(screen.getByLabelText('Titulo'), 'Autorizacion salida');
    await user.type(screen.getByLabelText('Contenido'), 'Autorizo salida anticipada');
    await user.type(screen.getByLabelText('Estudiante ID (opcional)'), '44');
    await user.click(screen.getByRole('button', { name: 'Firmar' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/apoderado/firmas/firmar/', {
        tipo_documento: 'AUTORIZACION',
        titulo: 'Autorizacion salida',
        contenido: 'Autorizo salida anticipada',
        estudiante_id: 44,
      });
    });

    expect(screen.getByText('Documento firmado correctamente.')).toBeInTheDocument();
  });

  it('shows loading state while panel data is being resolved', async () => {
    getMock.mockImplementation(() => new Promise(() => {}));

    renderWithProviders(<ApoderadoPage />);

    expect(screen.getAllByRole('status').length).toBeGreaterThan(0);
    // The submit button may exist but should be disabled during loading
    const firmarBtn = screen.queryByRole('button', { name: 'Firmar' });
    if (firmarBtn) {
      expect(firmarBtn).toBeDisabled();
    }
  });

  it('shows backend error when signing fails', async () => {
    const user = userEvent.setup();
    postMock.mockRejectedValueOnce({ payload: { detail: 'Firma rechazada por backend' } });

    renderWithProviders(<ApoderadoPage />);

    await screen.findByText(/Justificativos \(1\)/);

    await user.type(screen.getByLabelText('Titulo'), 'Autorizacion salida');
    await user.click(screen.getByRole('button', { name: 'Firmar' }));

    await waitFor(() => {
      expect(screen.getByText('Firma rechazada por backend')).toBeInTheDocument();
    });
  });
});
