import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { renderWithProviders, getMock } from '../../test/test-utils';

import DashboardPage from './DashboardPage';

function createExecutivePayload(scope = 'analytics') {
  return {
    scope,
    generated_at: '2026-03-07',
    kpis: {
      total_students: 342,
      total_teachers: 28,
      attendance_rate_today: 94.2,
      attendance_today_present: 323,
      attendance_today_total: 342,
      grades_below_threshold: 12,
      upcoming_evaluations: 6,
      active_classes: 20,
    },
    alerts: [{ type: 'warning', icon: '!', message: '12 estudiantes con notas bajo 4.0.' }],
    subscription_alert: { type: 'info', message: 'Plan vigente hasta fin de mes.' },
    usage_warnings: [{ type: 'danger', message: 'Se alcanzo el 90% del limite de almacenamiento.' }],
    recent_activity: [
      {
        type: 'evaluacion',
        icon: '*',
        title: 'Evaluacion creada',
        subject: 'Matematica',
        course: '2 Medio A',
        detail: 'Prueba parcial',
        timestamp: '2026-03-07T09:15:00',
      },
    ],
    charts: {
      attendance_trend_30d: [{ date: '2026-03-07', rate: 94.2, total: 342, present: 323 }],
      grade_distribution: [{ label: '4.0-5.0', count: 18, color: '#84cc16' }],
      attendance_by_course: [{ course: '2 Medio A', rate: 94.2, total: 34, present: 32 }],
    },
  };
}

function createDashboardPayload(scope) {
  if (scope === 'school') {
    return {
      contract_version: '1.0.0',
      scope: 'school',
      generated_at: '2026-03-07',
      available_scopes: ['school', 'self'],
      context: { is_global_admin: true },
      sections: {
        self: null,
        school: {
          today: '2026-03-07',
          students: 120,
          teachers: 18,
          courses_active: 6,
          classes_active: 24,
          attendance_today: 112,
          evaluations_upcoming: 4,
        },
        analytics: null,
      },
      charts: {},
    };
  }

  if (scope === 'analytics') {
    return {
      contract_version: '1.0.0',
      scope: 'analytics',
      generated_at: '2026-03-07',
      available_scopes: ['analytics'],
      sections: {
        self: null,
        school: null,
        analytics: {
          attendance_today_total: 342,
          attendance_today_present: 323,
          attendance_rate_today: 94.2,
          evaluations_next_7_days: 6,
          grades_below_approval: 12,
        },
      },
      charts: {},
    };
  }

  if (scope === 'global') {
    return {
      contract_version: '1.0.0',
      scope: 'global',
      generated_at: '2026-03-07',
      available_scopes: ['school', 'analytics', 'global'],
      context: { is_global_admin: true },
      sections: {
        self: null,
        school: {
          students: 420,
          teachers: 36,
          courses_active: 18,
          classes_active: 72,
          attendance_today: 390,
          evaluations_upcoming: 9,
        },
        analytics: {
          attendance_today_total: 420,
          attendance_today_present: 390,
          attendance_rate_today: 92.9,
          evaluations_next_7_days: 9,
          grades_below_approval: 15,
        },
      },
      charts: {},
    };
  }

  if (scope === 'self') {
    return {
      contract_version: '1.0.0',
      scope: 'self',
      generated_at: '2026-03-07',
      available_scopes: ['self', 'school'],
      sections: {
        self: { my_classes: 2, proximas_evaluaciones: [] },
        school: null,
        analytics: null,
      },
      charts: {},
    };
  }

  return {
    contract_version: '1.0.0',
    scope: 'school',
    generated_at: '2026-03-07',
    available_scopes: ['auto', 'school', 'self'],
    sections: {
      self: null,
      school: { students: 120, teachers: 18 },
      analytics: null,
    },
    charts: {},
  };
}

describe('DashboardPage', () => {
  beforeEach(() => {
    getMock.mockImplementation((path) => {
      if (path === '/api/v1/dashboard/resumen/?scope=school') return Promise.resolve(createDashboardPayload('school'));
      if (path === '/api/v1/dashboard/resumen/?scope=auto') return Promise.resolve(createDashboardPayload('auto'));
      if (path === '/api/v1/dashboard/resumen/?scope=analytics') return Promise.resolve(createDashboardPayload('analytics'));
      if (path === '/api/v1/dashboard/resumen/?scope=global') return Promise.resolve(createDashboardPayload('global'));
      if (path === '/api/v1/dashboard/resumen/?scope=self') return Promise.resolve(createDashboardPayload('self'));
      if (path === '/api/v1/dashboard/resumen/?scope=school&colegio_id=101') {
        return Promise.resolve({
          ...createDashboardPayload('school'),
          sections: {
            self: null,
            school: { students: 64, teachers: 8, courses_active: 4, classes_active: 16, attendance_today: 60, evaluations_upcoming: 2 },
            analytics: null,
          },
        });
      }
      if (path.startsWith('/api/v1/dashboard/executive/')) {
        const scope = path.includes('scope=global') ? 'global' : path.includes('scope=school') ? 'school' : 'analytics';
        return Promise.resolve(createExecutivePayload(scope));
      }
      if (path === '/api/v1/dashboard/colegios/') {
        return Promise.resolve({
          results: [
            { rbd: 101, nombre: 'Colegio Norte', slug: 'colegio-norte', comuna: 'Santiago' },
            { rbd: 202, nombre: 'Colegio Sur', slug: 'colegio-sur', comuna: 'Providencia' },
          ],
        });
      }
      return Promise.resolve({});
    });
  });

  it('loads school dashboard summary and executive detail', async () => {
    renderWithProviders(<DashboardPage />, {
      route: '/dashboard?scope=school',
      path: '/dashboard',
    });

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/resumen/?scope=school');
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/executive/?scope=school');
      expect(screen.getByText((content) => content.includes('Contrato 1.0.0'))).toBeInTheDocument();
      expect(screen.getByText('Estudiantes')).toBeInTheDocument();
      expect(screen.getByText('120')).toBeInTheDocument();
      expect(screen.getByText('Actividad reciente')).toBeInTheDocument();
    });
  });

  it('renders analytics metrics and executive alerts', async () => {
    renderWithProviders(<DashboardPage />, {
      route: '/dashboard?scope=analytics',
      path: '/dashboard',
    });

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/resumen/?scope=analytics');
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/executive/?scope=analytics');
      expect(screen.getByText('Analitica ejecutiva')).toBeInTheDocument();
      expect(screen.getByText('Tasa de asistencia')).toBeInTheDocument();
      expect(screen.getAllByText('94,2%').length).toBeGreaterThan(0);
      expect(screen.getByText('Plan vigente hasta fin de mes.')).toBeInTheDocument();
      expect(screen.getByText('Se alcanzo el 90% del limite de almacenamiento.')).toBeInTheDocument();
      expect(screen.getByText('12 estudiantes con notas bajo 4.0.')).toBeInTheDocument();
      expect(screen.getByText('Matematica - 2 Medio A')).toBeInTheDocument();
    });
  });

  it('renders global administrator metrics for global scope', async () => {
    renderWithProviders(<DashboardPage />, {
      route: '/dashboard?scope=global',
      path: '/dashboard',
    });

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/resumen/?scope=global');
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/executive/?scope=global');
      expect(screen.getByText('Panel global')).toBeInTheDocument();
      expect(screen.getByText('Administrador general', { exact: false })).toBeInTheDocument();
      expect(screen.getByText('Tasa asistencia global')).toBeInTheDocument();
      expect(screen.getByText('92,9%')).toBeInTheDocument();
    });
  });

  it('lets global administrators select a school for adapted school metrics', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DashboardPage />, {
      route: '/dashboard?scope=school',
      path: '/dashboard',
    });

    await waitFor(() => {
      expect(screen.getByLabelText('Colegio')).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText('Colegio'), '101');

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/resumen/?scope=school&colegio_id=101');
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/executive/?scope=school&colegio_id=101');
      expect(screen.getByText('64')).toBeInTheDocument();
    });
  });

  it('shows backend error when dashboard request fails', async () => {
    getMock.mockImplementation((path) => {
      if (path === '/api/v1/dashboard/resumen/?scope=self') {
        return Promise.reject({ payload: { detail: 'No autorizado para dashboard' } });
      }
      return Promise.resolve({});
    });

    renderWithProviders(<DashboardPage />, {
      route: '/dashboard?scope=self',
      path: '/dashboard',
    });

    await waitFor(() => {
      expect(screen.getByText('No autorizado para dashboard')).toBeInTheDocument();
    });
  });

  it('renders a structured loading state while dashboard data is fetching', () => {
    getMock.mockImplementation(() => new Promise(() => {}));

    renderWithProviders(<DashboardPage />, {
      route: '/dashboard?scope=analytics',
      path: '/dashboard',
    });

    const statusElements = screen.getAllByRole('status');
    expect(statusElements[0]).toHaveAttribute('aria-busy', 'true');
  });

  it('updates query and reloads when scope changes', async () => {
    const user = userEvent.setup();

    renderWithProviders(<DashboardPage />, {
      route: '/dashboard?scope=self',
      path: '/dashboard',
    });

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/resumen/?scope=self');
      expect(screen.getByRole('button', { name: /Colegio/ })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Colegio/ }));

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/dashboard/resumen/?scope=school');
    });
  });

  it('shows the student evaluations section even when there are no upcoming items', async () => {
    renderWithProviders(<DashboardPage />, {
      route: '/dashboard?scope=self',
      path: '/dashboard',
    });

    await waitFor(() => {
      expect(screen.getByText('No tienes evaluaciones proximas registradas.')).toBeInTheDocument();
    });
  });
});
