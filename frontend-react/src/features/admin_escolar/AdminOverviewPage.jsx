import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { apiClient } from '../../services/apiClient';
import { useFetch } from '../../hooks';
import { SummarySkeleton } from '../../components/feedback/TableLoadingState';
import { formatNumber, formatGrade } from '../../utils/formatters';

const SCOPES = ['school', 'analytics'];

export default function AdminOverviewPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialScope = searchParams.get('scope');
  const [scope, setScope] = useState(SCOPES.includes(initialScope) ? initialScope : 'school');
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [transitionMessage, setTransitionMessage] = useState('');
  const [transitionLoading, setTransitionLoading] = useState(false);

  const overviewUrl = `/api/v1/dashboard/resumen/?scope=${scope}`;
  const { data: overviewResp, loading: loadingOverview, error: overviewError, refetch: refetchOverview } = useFetch(overviewUrl);

  const { data: cyclesResp, loading: loadingCycles, error: cyclesError } = useFetch('/api/v1/ciclos-academicos/');
  const cycles = Array.isArray(cyclesResp?.results) ? cyclesResp.results : [];

  const cycleStatsUrl = selectedCycleId ? `/api/v1/ciclos-academicos/${selectedCycleId}/estadisticas/` : null;
  const { data: cycleStatsResp, loading: loadingCycleStats, error: cycleStatsError, refetch: refetchCycleStats } = useFetch(cycleStatsUrl, { skip: !selectedCycleId });
  const cycleStats = cycleStatsResp || null;

  const loading = loadingOverview || loadingCycles || loadingCycleStats || transitionLoading;
  const error = overviewError || cyclesError || cycleStatsError || '';

  useEffect(() => {
    const currentScope = searchParams.get('scope');
    if (currentScope === scope) {
      return;
    }
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('scope', scope);
    setSearchParams(nextParams, { replace: true });
  }, [scope, searchParams, setSearchParams]);

  useEffect(() => {
    // Trigger refetch when scope changes to keep data fresh.
    refetchOverview && refetchOverview();
  }, [scope]);

  useEffect(() => {
    if (!selectedCycleId) {
      return;
    }
    // refetch currently selected cycle stats
    refetchCycleStats && refetchCycleStats();
  }, [selectedCycleId]);

  async function refreshCycles() {
    const cyclesPayload = await apiClient.get('/api/v1/ciclos-academicos/');
    const cycleRows = Array.isArray(cyclesPayload?.results) ? cyclesPayload.results : [];
    if (!selectedCycleId && cycleRows.length) {
      setSelectedCycleId(String(cycleRows[0].id));
    }
    return cycleRows;
  }

  async function transitionCycle(nuevoEstado) {
    if (!selectedCycleId) {
      return;
    }
    setTransitionLoading(true);
    setTransitionMessage('');
    try {
      const payload = await apiClient.post(`/api/v1/ciclos-academicos/${selectedCycleId}/transicion/`, {
        nuevo_estado: nuevoEstado,
      });
      setTransitionMessage(
        `Transicion aplicada: ${payload.estado_anterior} -> ${payload.estado_actual}${
          Array.isArray(payload.warnings) && payload.warnings.length ? ` | Alertas: ${payload.warnings.join(' | ')}` : ''
        }`,
      );
      await refetchCycleStats?.();
      await refreshCycles();
    } catch (err) {
      setTransitionMessage(err.payload?.detail || err.payload?.nuevo_estado || 'No se pudo aplicar transicion.');
    } finally {
      setTransitionLoading(false);
    }
  }

  const metrics = useMemo(() => {
    const source = overviewResp || {};
    if (!source || !source.sections) return [];
    if (scope === 'school') {
      const school = source.sections.school || {};
      return [
        { title: 'Estudiantes', value: school.students },
        { title: 'Profesores', value: school.teachers },
        { title: 'Cursos Activos', value: school.courses_active },
        { title: 'Clases Activas', value: school.classes_active },
        { title: 'Asistencia Hoy', value: school.attendance_today },
        { title: 'Evaluaciones Proximas', value: school.evaluations_upcoming },
      ];
    }
    const analytics = source.sections.analytics || {};
    return [
      { title: 'Asistencias Hoy (Total)', value: analytics.attendance_today_total },
      { title: 'Asistencias Hoy (Presentes)', value: analytics.attendance_today_present },
      { title: 'Tasa Asistencia Hoy', value: `${analytics.attendance_rate_today ?? 0}%` },
      { title: 'Evaluaciones 7 Dias', value: analytics.evaluations_next_7_days },
      { title: 'Notas Bajo 4,0', value: analytics.grades_below_4 },
    ];
  }, [overviewResp, scope]);



  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="admin-overview-title">Panel Administrativo</h2>
          <p>Resumen general del colegio y gestión de ciclos académicos.</p>
        </div>
        <label>
          Vista
          <select value={scope} onChange={(e) => setScope(e.target.value)}>
            {SCOPES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </header>

      {error ? <div className="error-box" data-testid="admin-overview-error" role="alert" aria-live="assertive">{error}</div> : null}

      <div className="summary-grid" data-testid="admin-overview-summary">
        {loading
          ? Array.from({ length: scope === 'school' ? 6 : 5 }).map((_, index) => (
              <SummarySkeleton key={index} />
            ))
          : metrics.map((metric) => (
              <article key={metric.title} className="summary-tile">
                <small>{metric.title}</small>
                <strong>{formatNumber(metric.value) || '-'}</strong>
              </article>
            ))}
      </div>

      {!error ? (

          <article className="card section-card">
            <h3>Gestion de Ciclos Academicos</h3>
            <div className="actions section-card">
              <label>
                Ciclo
                <select value={selectedCycleId} onChange={(e) => setSelectedCycleId(e.target.value)}>
                  <option value="">Seleccionar</option>
                  {cycles.map((cycle) => (
                    <option key={cycle.id} value={cycle.id}>
                      {cycle.nombre} ({cycle.estado})
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {cycleStatsError ? <div className="error-box" role="alert" aria-live="assertive">{cycleStatsError}</div> : null}
            {transitionMessage ? <div className="info-box">{transitionMessage}</div> : null}

            {cycleStats ? (
              <>
                <div className="summary-grid">
                  <div className="summary-tile">
                    <small>Estado</small>
                    <strong>{cycleStats.ciclo?.estado || '-'}</strong>
                  </div>
                  <div className="summary-tile">
                    <small>Matriculas</small>
                    <strong>{cycleStats.matriculas?.total ?? 0}</strong>
                  </div>
                  <div className="summary-tile">
                    <small>Cursos activos</small>
                    <strong>{cycleStats.academico?.cursos ?? 0}</strong>
                  </div>
                  <div className="summary-tile">
                    <small>Promedio general</small>
                    <strong>{formatGrade(cycleStats.academico?.promedio_general, '-')}</strong>
                  </div>
                  <div className="summary-tile">
                    <small>Asistencia</small>
                    <strong>{cycleStats.academico?.porcentaje_asistencia ?? 0}%</strong>
                  </div>
                  <div className="summary-tile">
                    <small>Tasa cobranza</small>
                    <strong>{cycleStats.financiero?.tasa_cobranza ?? 0}%</strong>
                  </div>
                </div>

                <div className="actions-wrap section-card">
                  <button type="button" onClick={() => transitionCycle('PLANIFICACION')} disabled={transitionLoading || !selectedCycleId}>
                    PLANIFICACION
                  </button>
                  <button type="button" onClick={() => transitionCycle('ACTIVO')} disabled={transitionLoading || !selectedCycleId}>
                    ACTIVO
                  </button>
                  <button type="button" onClick={() => transitionCycle('EVALUACION')} disabled={transitionLoading || !selectedCycleId}>
                    EVALUACION
                  </button>
                  <button type="button" onClick={() => transitionCycle('FINALIZADO')} disabled={transitionLoading || !selectedCycleId}>
                    FINALIZADO
                  </button>
                  <button type="button" className="danger" onClick={() => transitionCycle('CERRADO')} disabled={transitionLoading || !selectedCycleId}>
                    CERRADO
                  </button>
                </div>
              </>
            ) : (
              <p>Selecciona un ciclo para ver estadisticas.</p>
            )}
          </article>
      ) : null}
    </section>
  );
}

