import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderWithProviders, paginated, getMock, postMock, patchMock, deleteMock, setupUser, clearUser } from '../../test/test-utils';
import AdminCoursesPage from './AdminCoursesPage';

describe('AdminCoursesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  it('loads course list for users with COURSE_VIEW', async () => {
    setupUser(['COURSE_VIEW']);
    getMock.mockResolvedValue(
      paginated([
        {
          id_curso: 10,
          nombre: '5A',
          activo: true,
          colegio_id: 123,
          nivel_id: 7,
          ciclo_academico_id: 2026,
        },
      ])
    );

    renderWithProviders(<AdminCoursesPage />, {
      route: '/admin/cursos',
      path: '/admin/cursos'
    });

    // Wait for data to load and render
    expect(await screen.findByText('5A')).toBeInTheDocument();
  });

  it('creates a new course when user has COURSE_CREATE', async () => {
    setupUser(['COURSE_VIEW', 'COURSE_CREATE']);
    const user = userEvent.setup({ delay: null });

    getMock
      .mockResolvedValueOnce(
        paginated([
          {
            id_curso: 10,
            nombre: '5A',
            activo: true,
            colegio_id: 123,
            nivel_id: 7,
            ciclo_academico_id: 2026,
          },
        ])
      )
      .mockResolvedValueOnce(
        paginated([
          {
            id_curso: 10,
            nombre: '5A',
            activo: true,
            colegio_id: 123,
            nivel_id: 7,
            ciclo_academico_id: 2026,
          },
          {
            id_curso: 11,
            nombre: '6B',
            activo: true,
            colegio_id: 123,
            nivel_id: 7,
            ciclo_academico_id: 2026,
          },
        ])
      );

    postMock.mockResolvedValue({
      id_curso: 11,
      nombre: '6B',
      activo: true,
      colegio_id: 123,
      nivel_id: 7,
      ciclo_academico_id: 2026,
    });

    renderWithProviders(<AdminCoursesPage />, {
      route: '/admin/cursos',
      path: '/admin/cursos'
    });

    // Wait for data to render
    expect(await screen.findByText('5A')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '+ Nuevo Curso' }));

    // Wait for overlay to appear
    await screen.findByRole('dialog');

    // Use fireEvent.change to set values directly to avoid overlay auto-focus issues
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: '6B' } });
    fireEvent.change(screen.getByLabelText('Nivel ID'), { target: { value: '7' } });
    fireEvent.change(screen.getByLabelText('Ciclo Academico ID (opcional)'), { target: { value: '2026' } });
    await user.click(screen.getByRole('button', { name: 'Crear' }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/cursos/', {
        nombre: '6B',
        activo: true,
        nivel_id: 7,
        ciclo_academico_id: 2026,
      });
    });
  });

  it('updates a course when user has COURSE_EDIT', async () => {
    setupUser(['COURSE_VIEW', 'COURSE_EDIT']);
    const user = userEvent.setup({ delay: null });
    getMock.mockResolvedValue(
      paginated([
        {
          id_curso: 10,
          nombre: '5A',
          activo: true,
          colegio_id: 123,
          nivel_id: 7,
          ciclo_academico_id: 2026,
        },
      ])
    );

    patchMock.mockResolvedValue({
      id_curso: 10,
      nombre: '5A Editado',
    });

    renderWithProviders(<AdminCoursesPage />, {
      route: '/admin/cursos',
      path: '/admin/cursos'
    });

    // Wait for data to render
    expect(await screen.findByText('5A')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Editar' }));

    // Wait for overlay to appear with edit mode title
    await screen.findByText('Editar curso #10');

    // Update name via fireEvent to avoid side effects
    const nameInput = screen.getByLabelText('Nombre');
    fireEvent.change(nameInput, { target: { value: '5A Editado' } });

    const submitButton = await screen.findByRole('button', { name: 'Actualizar' });
    await user.click(submitButton);

    await waitFor(() => {
      expect(patchMock).toHaveBeenCalledWith('/api/v1/cursos/10/', {
        nombre: '5A Editado',
        activo: true,
        nivel_id: 7,
        ciclo_academico_id: 2026,
      });
    });
  });

  it('deletes a course when user has COURSE_DELETE', async () => {
    setupUser(['COURSE_VIEW', 'COURSE_DELETE']);
    const user = userEvent.setup({ delay: null });
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    getMock
      .mockResolvedValueOnce(
        paginated([
          {
            id_curso: 10,
            nombre: '5A',
            activo: true,
            colegio_id: 123,
            nivel_id: 7,
            ciclo_academico_id: 2026,
          },
        ])
      )
      .mockResolvedValueOnce(paginated([]));

    deleteMock.mockResolvedValue(null);

    renderWithProviders(<AdminCoursesPage />, {
      route: '/admin/cursos',
      path: '/admin/cursos'
    });

    // Wait for data to render
    expect(await screen.findByText('5A')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Eliminar' }));

    await waitFor(() => {
      expect(deleteMock).toHaveBeenCalledWith('/api/v1/cursos/10/');
    });
  });

  it('shows restricted mode for read-only users', async () => {
    setupUser(['COURSE_VIEW']);
    getMock.mockResolvedValue(paginated([]));

    renderWithProviders(<AdminCoursesPage />, {
      route: '/admin/cursos',
      path: '/admin/cursos'
    });

    // Wait for data to load and table to render
    expect(await screen.findByText('Sin registros')).toBeInTheDocument();

    expect(screen.getByText(/Modo restringido: Solo lectura./)).toBeInTheDocument();
  });
});
