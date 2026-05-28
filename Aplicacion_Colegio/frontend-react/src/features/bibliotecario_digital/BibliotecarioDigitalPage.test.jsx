import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders, getMock, postMock, setupUser, clearUser } from '../../test/test-utils';
import BibliotecarioDigitalPage from './BibliotecarioDigitalPage';

describe('BibliotecarioDigitalPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    getMock.mockImplementation(async (path) => {
      if (path === '/api/bibliotecario/recursos/') {
        return { recursos: [{ id: 1, id_recurso: 1, titulo: 'Libro Matematica', tipo: 'LIBRO' }] };
      }
      if (path === '/api/bibliotecario/usuarios/') {
        return { usuarios: [{ id: 4, nombre: 'Carlos Ruiz' }] };
      }
      if (path === '/api/bibliotecario/prestamos/') {
        return { prestamos: [] };
      }
      return {};
    });
  });
  it('loads resources and users', async () => {
    setupUser(['LIBRARY_VIEW']);
    renderWithProviders(<BibliotecarioDigitalPage />);

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/bibliotecario/recursos/');
      expect(getMock).toHaveBeenCalledWith('/api/bibliotecario/usuarios/');
    });

    await screen.findByText(/Recursos \(1\)/);
    expect(screen.getByText('Préstamos activos')).toBeInTheDocument();
    expect(screen.getByText('Usuarios')).toBeInTheDocument();
  });

  it('shows loading state before the catalog is ready', () => {
    setupUser(['LIBRARY_VIEW']);
    getMock.mockImplementation(() => new Promise(() => {}));

    renderWithProviders(<BibliotecarioDigitalPage />);

    expect(screen.getAllByRole('status').length).toBeGreaterThan(0);
    // The button is always rendered but disabled when canCreate is false
    expect(screen.getByRole('button', { name: 'Crear recurso' })).toBeDisabled();
  });

  it('submits create resource with LIBRARY_CREATE', async () => {
    setupUser(['LIBRARY_CREATE']);
    const user = userEvent.setup({ delay: null });
    postMock.mockResolvedValueOnce({ message: 'Recurso creado.' });

    renderWithProviders(<BibliotecarioDigitalPage />);

    await screen.findByText(/Recursos \(1\)/);

    await user.type(screen.getByLabelText('Titulo'), 'Guia de Historia');
    await user.click(screen.getByRole('button', { name: 'Crear recurso' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/bibliotecario/recursos/crear/', {
        titulo: 'Guia de Historia',
        descripcion: '',
        tipo: 'DOCUMENTO',
        url_externa: '',
        publicado: false,
        es_plan_lector: false,
      });
    });
  });

  it('disables loan action without LIBRARY_MANAGE_LOANS', async () => {
    setupUser(['LIBRARY_VIEW']);
    renderWithProviders(<BibliotecarioDigitalPage />);

    await screen.findByText(/Recursos \(1\)/);
    const button = screen.getByRole('button', { name: 'Registrar prestamo' });
    expect(button).toBeDisabled();
  });

  it('shows backend error when create resource fails', async () => {
    setupUser(['LIBRARY_CREATE']);
    const user = userEvent.setup({ delay: null });
    postMock.mockRejectedValueOnce({ payload: { error: 'No se pudo crear recurso' } });

    renderWithProviders(<BibliotecarioDigitalPage />);

    await screen.findByText(/Recursos \(1\)/);

    await user.type(screen.getByLabelText('Titulo'), 'Guia de Historia');
    await user.click(screen.getByRole('button', { name: 'Crear recurso' }));

    await waitFor(() => {
      expect(screen.getByText('No se pudo crear recurso')).toBeInTheDocument();
    });
  });

  it('shows saving state while creating resource', async () => {
    setupUser(['LIBRARY_CREATE']);
    const user = userEvent.setup({ delay: null });
    postMock.mockReturnValueOnce(new Promise(() => {}));

    renderWithProviders(<BibliotecarioDigitalPage />);

    await screen.findByText(/Recursos \(1\)/);

    await user.type(screen.getByLabelText('Titulo'), 'Guia de Historia');
    await user.click(screen.getByRole('button', { name: 'Crear recurso' }));

    expect(screen.getByRole('button', { name: 'Guardando...' })).toBeDisabled();
  });

  it('submits toggle publish using resource selector', async () => {
    setupUser(['LIBRARY_EDIT']);
    const user = userEvent.setup({ delay: null });
    postMock.mockResolvedValueOnce({ message: 'Publicacion actualizada.' });

    renderWithProviders(<BibliotecarioDigitalPage />);

    await screen.findByText(/Recursos \(1\)/);

    const resourceSelects = screen.getAllByLabelText('Recurso');
    await user.selectOptions(resourceSelects[0], '1');
    await user.click(screen.getByRole('button', { name: 'Toggle publicar' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/bibliotecario/recursos/1/publicar/', {});
    });
  });
});
