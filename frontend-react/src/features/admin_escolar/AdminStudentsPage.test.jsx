import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders, getMock , setupUser } from '../../test/test-utils';

import AdminStudentsPage from './AdminStudentsPage';

const STUDENT_DATA = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      email: 'ana@example.com',
      rut: '11.111.111-1',
      nombre: 'Ana',
      apellido_paterno: 'Lagos',
      apellido_materno: 'Paz',
      is_active: true,
    },
    {
      id: 2,
      email: 'bruno@example.com',
      rut: '22.222.222-2',
      nombre: 'Bruno',
      apellido_paterno: 'Rojas',
      apellido_materno: 'Diaz',
      is_active: false,
    },
  ],
};

describe('AdminStudentsPage', () => {

  it('renders summary cards and student rows after data loads', async () => {
    getMock.mockImplementation(async (path) => {
      if (path.includes('/api/v1/estudiantes/')) {
        return STUDENT_DATA;
      }
      return { count: 0, next: null, previous: null, results: [] };
    });

    setupUser(['STUDENT_VIEW', 'STUDENT_EDIT']);
    renderWithProviders(<AdminStudentsPage />);

    // Wait for header
    await waitFor(() => {
      expect(screen.getByTestId('admin-students-title')).toBeInTheDocument();
    });

    // Wait for data to render
    expect(await screen.findByText('Ana Lagos')).toBeInTheDocument();
    expect(screen.getByText('Bruno Rojas')).toBeInTheDocument();

    // Summary cards should be visible
    expect(screen.getByText('Estudiantes visibles')).toBeInTheDocument();
    expect(screen.getByText('Activos')).toBeInTheDocument();
    expect(screen.getByText('Inactivos')).toBeInTheDocument();
  });

  it('supports row selection and bulk actions', async () => {
    const user = userEvent.setup();

    getMock.mockImplementation(async (path) => {
      if (path.includes('/api/v1/estudiantes/')) {
        return STUDENT_DATA;
      }
      return { count: 0, next: null, previous: null, results: [] };
    });

    setupUser(['STUDENT_VIEW', 'STUDENT_EDIT']);
    renderWithProviders(<AdminStudentsPage />);

    // Wait for data to render
    expect(await screen.findByText('Ana Lagos')).toBeInTheDocument();
    expect(screen.getByText('Bruno Rojas')).toBeInTheDocument();

    // Select a row
    const rowCheckboxes = screen.getAllByRole('checkbox');
    await user.click(rowCheckboxes[1]);

    expect(screen.getByText('1 seleccionado(s) en la pagina actual.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Desactivar Seleccionados' })).toBeEnabled();
  });
});