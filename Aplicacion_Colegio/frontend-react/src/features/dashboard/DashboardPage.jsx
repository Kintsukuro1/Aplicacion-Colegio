import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { Card, CardHeader, CardBody, Badge, Button } from '@/components/ui';
import { apiClient } from '@/lib/apiClient';

const EXECUTIVE_SCOPES = new Set(['school', 'analytics', 'global']);

function buildDashboardPath(basePath, scope, schoolId) {
  const params = new URLSearchParams({ scope });
  if (schoolId) params.set('colegio_id', schoolId);
  return `${basePath}?${params.toString()}`;
}

function fetchDashboardResumen(scope, schoolId) {
  return apiClient.get(buildDashboardPath('/api/v1/dashboard/resumen/', scope, schoolId));
}

function fetchDashboardExecutive(scope, schoolId) {
  return apiClient.get(buildDashboardPath('/api/v1/dashboard/executive/', scope, schoolId));
}

function fetchDashboardSchools() {
  return apiClient.get('/api/v1/dashboard/colegios/');
}

function formatValue(value, suffix = '') {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'number') return `${new Intl.NumberFormat('es-CL').format(value)}${suffix}`;
  return `${value}${suffix}`;
}

function formatDateTime(value) {
  if (!value) return '';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toLocaleString('es-CL');
}

export default function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const scope = searchParams.get('scope') || 'auto';
  const selectedSchoolId = searchParams.get('colegio_id') || '';

  const { data: resumen, isLoading: loadingResumen, error: errorResumen } = useQuery({
    queryKey: ['dashboard', 'resumen', scope, selectedSchoolId],
    queryFn: () => fetchDashboardResumen(scope, selectedSchoolId),
    retry: 0,
  });

  const actualScope = resumen?.scope;
  const shouldLoadExecutive = EXECUTIVE_SCOPES.has(actualScope);
  const { data: executive, isLoading: loadingExec, error: errorExec } = useQuery({
    queryKey: ['dashboard', 'executive', actualScope, selectedSchoolId],
    queryFn: () => fetchDashboardExecutive(actualScope, selectedSchoolId),
    enabled: shouldLoadExecutive,
    retry: 0,
  });

  const isGlobalContext = Boolean(resumen?.context?.is_global_admin);
  const { data: schoolsPayload, isLoading: loadingSchools } = useQuery({
    queryKey: ['dashboard', 'schools'],
    queryFn: fetchDashboardSchools,
    enabled: isGlobalContext,
    retry: 0,
  });

  const isLoading = loadingResumen || (shouldLoadExecutive && loadingExec);

  if (errorResumen) {
    const msg = errorResumen.payload?.detail || errorResumen.message || 'Error al cargar';
    return <div className="p-6 text-red-600">{msg}</div>;
  }

  if (isLoading) {
    return (
      <div className="p-6" role="status" aria-busy="true">
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-4 py-1">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!resumen) return null;

  const availableScopes = resumen.available_scopes || [];
  const schools = schoolsPayload?.results || [];

  function handleScopeChange(newScope) {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('scope', newScope);
    setSearchParams(nextParams);
  }

  function handleSchoolChange(newSchoolId) {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('scope', 'school');
    if (newSchoolId) {
      nextParams.set('colegio_id', newSchoolId);
    } else {
      nextParams.delete('colegio_id');
    }
    setSearchParams(nextParams);
  }

  const scopeLabels = {
    self: 'Personal',
    school: isGlobalContext ? 'Colegio adaptado' : 'Colegio',
    analytics: 'Analitica',
    global: 'Global',
    auto: 'Automatico',
  };

  const title =
    actualScope === 'analytics'
      ? 'Analitica ejecutiva'
      : actualScope === 'global'
        ? 'Panel global'
        : actualScope === 'school' && isGlobalContext
          ? 'Panel de colegio adaptado'
          : 'Dashboard';

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:justify-between lg:items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
          <p className="text-gray-500 text-sm mt-1">
            Contrato {resumen.contract_version}
            {isGlobalContext ? ' - Administrador general' : ''}
          </p>
        </div>

        {availableScopes.length > 1 && (
          <div className="flex flex-wrap gap-2 bg-gray-100 p-1 rounded-lg">
            {availableScopes.filter((s) => s !== 'auto').map((s) => (
              <Button
                key={s}
                variant={actualScope === s ? 'primary' : 'ghost'}
                onClick={() => handleScopeChange(s)}
              >
                {scopeLabels[s] || s}
              </Button>
            ))}
          </div>
        )}
      </div>

      {errorExec ? (
        <div className="bg-yellow-50 text-yellow-800 p-4 rounded-lg border border-yellow-200">
          No se pudo cargar el detalle ejecutivo. Se muestran las metricas disponibles del resumen.
        </div>
      ) : null}

      {actualScope === 'school' && (
        <SchoolDashboard
          resumen={resumen}
          executive={executive}
          isGlobalContext={isGlobalContext}
          schools={schools}
          selectedSchoolId={selectedSchoolId}
          loadingSchools={loadingSchools}
          onSchoolChange={handleSchoolChange}
        />
      )}
      {actualScope === 'analytics' && <AnalyticsDashboard resumen={resumen} executive={executive} />}
      {actualScope === 'global' && <GlobalDashboard resumen={resumen} executive={executive} />}
      {actualScope === 'self' && <SelfDashboard resumen={resumen} />}
    </div>
  );
}

function MetricCard({ title, value, suffix = '', detail = '', tone = 'gray' }) {
  const tones = {
    gray: 'text-gray-900',
    blue: 'text-blue-600',
    green: 'text-green-600',
    red: 'text-red-600',
    amber: 'text-orange-600',
    purple: 'text-purple-600',
  };

  return (
    <Card variant="hover_lift">
      <CardBody>
        <div className="text-center p-2">
          <p className="text-gray-500">{title}</p>
          <p className={`text-4xl font-bold mt-2 ${tones[tone] || tones.gray}`}>{formatValue(value, suffix)}</p>
          {detail ? <p className="text-xs text-gray-400 mt-1">{detail}</p> : null}
        </div>
      </CardBody>
    </Card>
  );
}

function SchoolDashboard({ resumen, executive, isGlobalContext, schools, selectedSchoolId, loadingSchools, onSchoolChange }) {
  const schoolData = resumen.sections?.school || {};
  const kpis = executive?.kpis || {};
  const selectedSchool = schools.find((school) => String(school.rbd) === String(selectedSchoolId));

  return (
    <div className="space-y-6">
      {isGlobalContext ? (
        <div className="bg-blue-50 text-blue-900 p-4 rounded-lg border border-blue-200 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="font-semibold">Vista adaptada para administrador general</p>
            <p className="text-sm text-blue-800">
              {selectedSchool
                ? `Mostrando metricas de ${selectedSchool.nombre}.`
                : 'Selecciona un colegio para ver sus metricas especificas, o deja la opcion agregada.'}
            </p>
          </div>
          <label className="flex flex-col gap-1 text-sm font-medium text-blue-900 min-w-64">
            Colegio
            <select
              value={selectedSchoolId}
              onChange={(event) => onSchoolChange(event.target.value)}
              disabled={loadingSchools}
              className="rounded-md border border-blue-200 bg-white px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
            >
              <option value="">{loadingSchools ? 'Cargando colegios...' : 'Todos los colegios'}</option>
              {schools.map((school) => (
                <option key={school.rbd} value={school.rbd}>
                  {school.nombre} ({school.rbd})
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Estudiantes" value={schoolData.students ?? kpis.total_students} tone="blue" />
        <MetricCard title="Profesores" value={schoolData.teachers ?? kpis.total_teachers} tone="green" />
        <MetricCard title="Cursos activos" value={schoolData.courses_active} tone="purple" />
        <MetricCard title="Clases activas" value={schoolData.classes_active ?? kpis.active_classes} tone="amber" />
        <MetricCard title="Asistencias hoy" value={schoolData.attendance_today} />
        <MetricCard title="Evaluaciones proximas" value={schoolData.evaluations_upcoming ?? kpis.upcoming_evaluations} />
        <MetricCard title="Asistencia ejecutiva" value={kpis.attendance_rate_today} suffix="%" detail={`${kpis.attendance_today_present || 0} / ${kpis.attendance_today_total || 0} presentes`} tone="blue" />
        <MetricCard title="Alertas academicas" value={kpis.grades_below_threshold} detail="Estudiantes bajo umbral" tone="red" />
      </div>

      {executive ? <ExecutiveDetails executive={executive} /> : null}
    </div>
  );
}

function AnalyticsDashboard({ resumen, executive }) {
  const analytics = resumen.sections?.analytics || {};
  const kpis = executive?.kpis || {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Asistencias hoy" value={analytics.attendance_today_total ?? kpis.attendance_today_total} />
        <MetricCard title="Presentes hoy" value={analytics.attendance_today_present ?? kpis.attendance_today_present} tone="green" />
        <MetricCard title="Tasa de asistencia" value={analytics.attendance_rate_today ?? kpis.attendance_rate_today} suffix="%" tone="blue" />
        <MetricCard title="Evaluaciones 7 dias" value={analytics.evaluations_next_7_days ?? kpis.upcoming_evaluations} tone="purple" />
        <MetricCard title="Notas bajo aprobacion" value={analytics.grades_below_approval ?? kpis.grades_below_threshold} detail={`Umbral ${analytics.nota_aprobacion ?? 4.0}`} tone="red" />
        <MetricCard title="Clases activas" value={kpis.active_classes} tone="amber" />
      </div>

      {executive ? <ExecutiveDetails executive={executive} /> : null}
    </div>
  );
}

function GlobalDashboard({ resumen, executive }) {
  const school = resumen.sections?.school || {};
  const analytics = resumen.sections?.analytics || {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Estudiantes" value={school.students} tone="blue" />
        <MetricCard title="Profesores" value={school.teachers} tone="green" />
        <MetricCard title="Cursos activos" value={school.courses_active} tone="purple" />
        <MetricCard title="Clases activas" value={school.classes_active} tone="amber" />
        <MetricCard title="Tasa asistencia global" value={analytics.attendance_rate_today} suffix="%" tone="blue" />
        <MetricCard title="Evaluaciones 7 dias" value={analytics.evaluations_next_7_days} />
        <MetricCard title="Notas bajo aprobacion" value={analytics.grades_below_approval} tone="red" />
        <MetricCard title="Asistencias hoy" value={analytics.attendance_today_total} />
      </div>

      {executive ? <ExecutiveDetails executive={executive} /> : null}
    </div>
  );
}

function ExecutiveDetails({ executive }) {
  const alerts = executive.alerts || [];
  const usageWarnings = executive.usage_warnings || [];
  const subscriptionAlert = executive.subscription_alert;
  const activity = executive.recent_activity || [];
  const charts = executive.charts || {};
  const trend = charts.attendance_trend_30d || [];

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        {subscriptionAlert ? (
          <div className="bg-blue-50 text-blue-800 p-4 rounded-lg border border-blue-200">{subscriptionAlert.message}</div>
        ) : null}
        {usageWarnings.map((warning, i) => (
          <div key={`usage-${i}`} className="bg-red-50 text-red-800 p-4 rounded-lg border border-red-200">
            {warning.message}
          </div>
        ))}
        {alerts.map((alert, i) => (
          <div key={`alert-${i}`} className="bg-yellow-50 text-yellow-800 p-4 rounded-lg border border-yellow-200 flex items-center gap-2">
            {alert.icon ? <span>{alert.icon}</span> : null}
            {alert.message}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card variant="default" className="lg:col-span-2">
          <CardHeader title="Tendencia de asistencia" subtitle="Ultimos 30 dias" />
          <CardBody>
            <div className="flex items-end gap-1 h-32 mt-2">
              {trend.slice(-30).map((item) => (
                <div key={item.date} className="flex-1 bg-blue-100 rounded-t" title={`${item.date}: ${item.rate}%`}>
                  <div className="bg-blue-600 rounded-t" style={{ height: `${Math.max(item.rate || 0, 4)}%` }}></div>
                </div>
              ))}
              {trend.length === 0 ? <p className="text-gray-500 text-sm py-4">No hay tendencia de asistencia disponible.</p> : null}
            </div>
          </CardBody>
        </Card>

        <Card variant="default">
          <CardHeader title="Asistencia por curso" subtitle="Mes actual" />
          <CardBody>
            <div className="space-y-3 mt-2">
              {(charts.attendance_by_course || []).slice(0, 6).map((course, idx) => (
                <div key={`${course.course}-${idx}`} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <span className="font-medium text-gray-800 text-sm">{course.course}</span>
                  <Badge variant={course.rate >= 85 ? 'success' : course.rate >= 70 ? 'warning' : 'error'}>{course.rate}%</Badge>
                </div>
              ))}
              {(!charts.attendance_by_course || charts.attendance_by_course.length === 0) ? (
                <p className="text-gray-500 text-sm text-center py-4">No hay datos de asistencia suficientes.</p>
              ) : null}
            </div>
          </CardBody>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card variant="default">
          <CardHeader title="Distribucion de notas" subtitle="Rendimiento general" />
          <CardBody>
            <div className="space-y-4 mt-2">
              {(charts.grade_distribution || []).map((item, idx) => (
                <div key={`${item.label}-${idx}`}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600 font-medium">{item.label}</span>
                    <span className="text-gray-900">{item.count} registros</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className="h-2 rounded-full" style={{ width: `${Math.min((item.count || 0) * 8, 100)}%`, backgroundColor: item.color }}></div>
                  </div>
                </div>
              ))}
              {(!charts.grade_distribution || charts.grade_distribution.length === 0) ? (
                <p className="text-gray-500 text-sm py-4">No hay calificaciones suficientes.</p>
              ) : null}
            </div>
          </CardBody>
        </Card>

        <Card variant="default">
          <CardHeader title="Actividad reciente" />
          <CardBody>
            {activity.length === 0 ? (
              <p className="text-gray-500 py-4">No hay actividad reciente.</p>
            ) : (
              <div className="space-y-4">
                {activity.map((act, i) => (
                  <div key={`${act.type}-${i}`} className="flex gap-4 border-b border-gray-100 pb-4 last:border-0 last:pb-0">
                    <div className="text-2xl pt-1">{act.icon}</div>
                    <div>
                      <p className="font-medium text-gray-900">{act.title}</p>
                      <p className="text-sm text-gray-600">{[act.subject, act.course].filter(Boolean).join(' - ')}</p>
                      <p className="text-sm text-gray-500 exec-activity-time">{[act.detail, formatDateTime(act.timestamp)].filter(Boolean).join(' - ')}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function SelfDashboard({ resumen }) {
  const selfData = resumen.sections?.self || {};
  const evalList = selfData.proximas_evaluaciones || [];
  const role = (selfData.role || '').toLowerCase();
  const isAdmin = role.includes('administrador');

  if (isAdmin) {
    const metrics = [
      { title: 'Matriculas activas', value: selfData.matriculas_activas, tone: 'blue' },
      { title: 'Estudiantes', value: selfData.total_estudiantes, tone: 'green' },
      { title: 'Profesores', value: selfData.total_profesores, tone: 'purple' },
      { title: 'Cursos activos', value: selfData.total_cursos, tone: 'amber' },
      { title: 'Asistencia del mes', value: selfData.asistencia_promedio_mes, suffix: '%', tone: 'blue' },
      { title: 'Morosidad', value: selfData.total_morosidad, tone: 'red' },
      { title: 'Alumnos morosos', value: selfData.alumnos_morosos, tone: 'red' },
      { title: 'Evaluaciones proximas', value: selfData.evaluaciones_proximas, tone: 'purple' },
    ];

    if (selfData.suscripciones_activas !== undefined) {
      metrics.push({ title: 'Suscripciones activas', value: selfData.suscripciones_activas, tone: 'green' });
      metrics.push({ title: 'Suscripciones vencidas', value: selfData.suscripciones_vencidas, tone: 'red' });
    }

    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {metrics.map((metric) => (
            <MetricCard key={metric.title} {...metric} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card variant="default">
        <CardHeader title="Mis evaluaciones proximas" />
        <CardBody>
          {evalList.length === 0 ? (
            <p className="text-gray-500 py-4">No tienes evaluaciones proximas registradas.</p>
          ) : (
            <ul className="space-y-2">
              {evalList.map((ev, i) => (
                <li key={`${ev.nombre || ev.title}-${i}`} className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                  {ev.nombre || ev.title}
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
