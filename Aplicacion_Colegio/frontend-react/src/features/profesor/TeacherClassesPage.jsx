import { useMemo, useState } from 'react';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../services/apiClient';
import { SummarySkeleton } from '../../components/feedback/TableLoadingState';
import { formatNumber, formatGrade } from '../../utils/formatters';

function formatPercentage(value) {
  if (value === null || value === undefined || value === '') {
    return '-';
  }

  return `${formatNumber(value, '-')}%`;
}

export default function TeacherClassesPage() {
  const [periodo, setPeriodo] = useState('semestre');
  const [selectedClassId, setSelectedClassId] = useState('');

  // Load classes
  const { data: classesResp, isLoading: loading, error: errorObj } = useQuery({
    queryKey: ['profesor-clases'],
    queryFn: () => apiClient.get('/api/v1/profesor/clases/')
  });
  const error = errorObj?.message;
  const rows = (classesResp?.results || []);

  // Build trends URL with parameters
  const trendsParams = new URLSearchParams({ periodo });
  if (selectedClassId) {
    trendsParams.set('clase_id', selectedClassId);
  }
  const trendsUrl = `/api/v1/profesor/tendencias/?${trendsParams.toString()}`;
  const { data: trends, isLoading: loadingTrends, error: trendsErrorObj } = useQuery({
    queryKey: ['profesor-tendencias', periodo, selectedClassId],
    queryFn: () => apiClient.get(trendsUrl)
  });
  const trendsError = trendsErrorObj?.message;

  // Load schedule
  const { data: schedule, isLoading: loadingSchedule, error: scheduleErrorObj } = useQuery({
    queryKey: ['profesor-horario'],
    queryFn: () => apiClient.get('/api/v1/profesor/mi-horario/')
  });
  const scheduleError = scheduleErrorObj?.message;

  // Validate selectedClassId against loaded classes
  if (selectedClassId && !rows.some((row) => String(row.id) === String(selectedClassId))) {
    setSelectedClassId('');
  }

  const summary = useMemo(() => {
    const totalClasses = rows.length;
    const activeClasses = rows.filter((row) => row.activo).length;
    const totalStudents = rows.reduce((acc, row) => acc + (Number(row.total_estudiantes) || 0), 0);
    const averageAttendance = trends?.tendencia_general?.porcentaje_asistencia;
    const averageGrade = trends?.tendencia_general?.promedio_general;

    return [
      {
        title: 'Clases cargadas',
        value: totalClasses,
        subtitle: totalClasses > 0 ? `${activeClasses} activas` : 'Sin clases por ahora',
      },
      {
        title: 'Estudiantes',
        value: totalStudents,
        subtitle: totalStudents > 0 ? 'Distribuidos en tus cursos' : 'Sin estudiantes registrados',
      },
      {
        title: 'Promedio general',
        value: averageGrade !== undefined && averageGrade !== null ? formatGrade(averageGrade, '-') : '-',
        subtitle: averageGrade ? 'Del periodo seleccionado' : 'Sin datos de promedio',
      },
      {
        title: 'Asistencia general',
        value: averageAttendance !== undefined && averageAttendance !== null ? formatPercentage(averageAttendance) : '-',
        subtitle: averageAttendance !== undefined ? 'Consolidado de tendencias' : 'Sin datos de asistencia',
      },
    ];
  }, [rows, trends]);

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="teacher-classes-title">Profesor: Mis Clases</h2>
          <p>Vista operativa de clases, tendencias y horario semanal.</p>
        </div>
      </header>

      {error ? <div className="error-box" data-testid="teacher-classes-error" role="alert" aria-live="assertive">{error}</div> : null}

      <div className="summary-grid" data-testid="teacher-classes-summary">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => (
              <SummarySkeleton key={index} />
            ))
          : summary.map((item) => (
              <article key={item.title} className="summary-tile">
                <small>{item.title}</small>
                <strong>{item.value}</strong>
                <span>{item.subtitle}</span>
              </article>
            ))}
      </div>

      {!error ? (
        <div className="grid-2">
          <article className="card section-card">
            <div className="section-card-head">
              <div>
                <h3>Tendencias del Profesor</h3>
                <p>Filtra por periodo y clase para ver la evolución del curso.</p>
              </div>
            </div>

            <div className="actions">
              <label>
                Periodo
                <select value={periodo} onChange={(e) => setPeriodo(e.target.value)}>
                  <option value="mes">Mes</option>
                  <option value="semestre">Semestre</option>
                  <option value="anual">Anual</option>
                </select>
              </label>
              <label>
                Clase
                <select value={selectedClassId} onChange={(e) => setSelectedClassId(e.target.value)}>
                  <option value="">Todas</option>
                  {rows.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.curso_nombre} - {row.asignatura_nombre}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {loadingTrends ? <p>Cargando tendencias…</p> : null}
            {trendsError ? <div className="error-box" role="alert" aria-live="assertive">{trendsError}</div> : null}

            {!loadingTrends && !trendsError && trends?.tendencia_general ? (
              <div className="summary-grid section-card">
                <article className="summary-tile">
                  <small>Promedio general</small>
                  <strong>{formatGrade(trends.tendencia_general.promedio_general, '-')}</strong>
                </article>
                <article className="summary-tile">
                  <small>Asistencia general</small>
                  <strong>{formatPercentage(trends.tendencia_general.porcentaje_asistencia)}</strong>
                </article>
                <article className="summary-tile">
                  <small>Total clases</small>
                  <strong>{trends.tendencia_general.total_clases ?? 0}</strong>
                </article>
              </div>
            ) : null}

            {!loadingTrends && !trendsError && !trends?.tendencia_general ? (
              <p className="section-muted">No hay tendencias disponibles para el periodo seleccionado.</p>
            ) : null}

            {!loadingTrends && !trendsError && Array.isArray(trends?.asistencia_mensual) && trends.asistencia_mensual.length ? (
              <div className="monthly-list section-card">
                <h4>Asistencia mensual</h4>
                <ul>
                  {trends.asistencia_mensual.map((item) => (
                    <li key={item.mes}>
                      {item.mes}: {item.porcentaje}% ({item.total_registros} registros)
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {!loadingTrends && !trendsError && Array.isArray(trends?.asistencia_mensual) && trends.asistencia_mensual.length === 0 ? (
              <p className="section-muted">No hay registro mensual para graficar.</p>
            ) : null}
          </article>

          <article className="card section-card">
            <div className="section-card-head">
              <div>
                <h3>Mi Horario Semanal</h3>
                <p>Bloques asignados para hoy y el resto de la semana.</p>
              </div>
            </div>
            {loadingSchedule ? <p>Cargando horario…</p> : null}
            {scheduleError ? <div className="error-box" role="alert" aria-live="assertive">{scheduleError}</div> : null}

            {!loadingSchedule && !scheduleError && schedule ? (
              <>
                <div className="summary-grid section-card">
                  <article className="summary-tile">
                    <small>Bloques totales</small>
                    <strong>{schedule.total_bloques ?? 0}</strong>
                  </article>
                  <article className="summary-tile">
                    <small>Días con clases</small>
                    <strong>{Object.keys(schedule.horario || {}).filter((dia) => Array.isArray(schedule.horario[dia]) && schedule.horario[dia].length).length}</strong>
                  </article>
                </div>

                <div className="grid-2">
                  {Object.entries(schedule.horario || {}).map(([dia, bloques]) => (
                    <article key={dia} className="card info-box">
                      <h4>{dia}</h4>
                      {Array.isArray(bloques) && bloques.length ? (
                        <ul>
                          {bloques.map((bloque) => (
                            <li key={bloque.id || `${dia}-${bloque.bloque_numero}-${bloque.hora_inicio}`}>
                              <strong>Bloque {bloque.bloque_numero}</strong>
                              <span>{bloque.hora_inicio} - {bloque.hora_fin}</span>
                              <span>{bloque.curso_nombre} / {bloque.asignatura_nombre}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p>Sin bloques asignados.</p>
                      )}
                    </article>
                  ))}
                </div>
              </>
            ) : null}

            {!loadingSchedule && !scheduleError && !schedule ? (
              <p className="section-muted">No fue posible construir el horario semanal.</p>
            ) : null}
          </article>
        </div>
      ) : null}

      {!loading && !error ? (
        <article className="card section-card">
          <div className="section-card-head">
            <div>
              <h3>Clases Asignadas</h3>
              <p>Listado operativo con acceso directo a tus clases.</p>
            </div>
          </div>

          {rows.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Curso</th>
                    <th>Asignatura</th>
                    <th>Estudiantes</th>
                    <th>Activa</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id}>
                      <td>{row.id}</td>
                      <td>{row.curso_nombre}</td>
                      <td>{row.asignatura_nombre}</td>
                      <td>{row.total_estudiantes}</td>
                      <td>{row.activo ? 'Si' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>No tienes clases asignadas todavía.</p>
          )}
        </article>
      ) : null}
    </section>
  );
}

