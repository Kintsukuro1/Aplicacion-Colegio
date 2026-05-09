import { useMemo, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/apiClient';
import { SummarySkeleton } from '../../components/TableLoadingState';
import { formatNumber } from '../../lib/formatters';

function formatPercentage(value) {
  if (value === null || value === undefined || value === '') {
    return '-';
  }

  return `${formatNumber(value, '-')}%`;
}

function buildAverage(items) {
  const numericValues = items
    .map((item) => Number(item?.promedio))
    .filter((value) => !Number.isNaN(value));

  if (!numericValues.length) {
    return null;
  }

  const total = numericValues.reduce((acc, value) => acc + value, 0);
  return total / numericValues.length;
}



function SectionStatus({ title, description, loading = false }) {
  return (
    <div
      className="card section-card"
      aria-busy={loading ? 'true' : 'false'}
      aria-live="polite"
      role={loading ? 'status' : undefined}
      style={{ background: 'rgba(148, 163, 184, 0.06)' }}
    >
      <strong>{title}</strong>
      <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>{description}</p>
      {loading ? <div style={{ marginTop: '1rem', height: '12px', width: '60%', borderRadius: '999px', background: 'rgba(148, 163, 184, 0.14)' }} /> : null}
    </div>
  );
}

function EmptySection({ title, description }) {
  return (
    <div className="card section-card" style={{ background: 'rgba(148, 163, 184, 0.04)' }}>
      <strong>{title}</strong>
      <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>{description}</p>
    </div>
  );
}

export default function StudentSelfPage() {
  const location = useLocation();
  const [selectedCycle, setSelectedCycle] = useState('');

  const { data: profile, isLoading: loadingProfile, error: profileErrorObj } = useQuery({
    queryKey: ['student-profile'],
    queryFn: () => apiClient.get('/api/v1/estudiante/mi-perfil/')
  });
  const { data: classesData = [], isLoading: loadingClasses, error: classesErrorObj } = useQuery({
    queryKey: ['student-classes'],
    queryFn: () => apiClient.get('/api/v1/estudiante/mis-clases/')
  });
  const { data: gradesData = [], isLoading: loadingGrades, error: gradesErrorObj } = useQuery({
    queryKey: ['student-grades'],
    queryFn: () => apiClient.get('/api/v1/estudiante/mis-notas/')
  });
  const { data: attendanceData = [], isLoading: loadingAttendance, error: attendanceErrorObj } = useQuery({
    queryKey: ['student-attendance'],
    queryFn: () => apiClient.get('/api/v1/estudiante/mi-asistencia/')
  });

  const profileError = profileErrorObj?.message;
  const classesError = classesErrorObj?.message;
  const gradesError = gradesErrorObj?.message;
  const attendanceError = attendanceErrorObj?.message;
  
  const classes = Array.isArray(classesData) ? classesData : [];
  const grades = Array.isArray(gradesData) ? gradesData : [];
  const attendance = Array.isArray(attendanceData) ? attendanceData : [];

  const historyUrl = selectedCycle 
    ? `/api/v1/estudiante/historial-academico/?ciclo=${selectedCycle}`
    : '/api/v1/estudiante/historial-academico/';
  const { 
    data: history, 
    isLoading: loadingHistory, 
    error: historyErrorObj 
  } = useQuery({
    queryKey: ['student-history', selectedCycle],
    queryFn: () => apiClient.get(historyUrl)
  });
  const historyError = historyErrorObj?.message;

  // We need an effect to sync selectedCycle based on the loaded history
  useEffect(() => {
    if (!selectedCycle && history?.ciclo?.id) {
      setSelectedCycle(String(history.ciclo.id));
    }
  }, [history, selectedCycle]);

  const summaryLoading = loadingProfile || loadingClasses || loadingGrades || loadingAttendance || loadingHistory;
  const hasAnyError = profileError || classesError || gradesError || attendanceError || historyError;

  const quickLinks = [
    { id: 'student-profile', label: 'Mi Perfil' },
    { id: 'student-classes', label: 'Mis Clases' },
    { id: 'student-grades', label: 'Mis Notas' },
    { id: 'student-attendance', label: 'Mi Asistencia' },
    { id: 'student-history', label: 'Historial Académico' },
  ];

  function scrollToSection(id) {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  useEffect(() => {
    if (!location.hash) {
      return;
    }

    const target = location.hash.slice(1);
    window.setTimeout(() => scrollToSection(target), 0);
  }, [location.hash, summaryLoading]);

  const profileCards = useMemo(() => {
    const subjectCount = classes.length;
    const gradeAverage = buildAverage(history?.asignaturas || []);
    const attendanceAverage = history?.asignaturas?.length
      ? buildAverage(history.asignaturas.map((item) => ({ promedio: item.porcentaje_asistencia })))
      : null;
    const pendingTasks = Array.isArray(grades)
      ? grades.reduce((acc, item) => acc + (Number(item?.pendientes) || 0), 0)
      : 0;

    return [
      {
        title: 'Mi Curso',
        value: profile?.curso_actual || profile?.curso || 'Sin curso',
        subtitle: profile?.colegio || profile?.escuela || 'Perfil estudiante',
      },
      {
        title: 'Asignaturas',
        value: subjectCount,
        subtitle: subjectCount > 0 ? 'Clases activas en el ciclo' : 'Sin clases registradas',
      },
      {
        title: 'Promedio general',
        value: gradeAverage !== null ? formatNumber(gradeAverage, '-') : '-',
        subtitle: gradeAverage !== null ? 'Promedio ponderado del historial' : 'Aún no hay notas suficientes',
      },
      {
        title: 'Asistencia',
        value: attendanceAverage !== null ? formatPercentage(attendanceAverage) : '-',
        subtitle: attendanceAverage !== null ? 'Promedio del ciclo actual' : 'Sin datos de asistencia',
      },
      {
        title: 'Tareas pendientes',
        value: pendingTasks,
        subtitle: pendingTasks > 0 ? 'Revisa tareas abiertas' : 'Sin tareas pendientes',
      },
    ];
  }, [classes.length, grades, history, profile]);

  const historyAverage = useMemo(() => buildAverage(history?.asignaturas || []), [history]);

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>Estudiante: Mi Panel</h2>
          <p>Resumen personal con perfil, clases, notas, asistencia e historial académico.</p>
        </div>
      </header>

      <article className="card section-card" aria-label="Navegación rápida del panel de estudiante">
        <h3>Accesos rápidos</h3>
        <div className="actions-wrap">
          {quickLinks.map((link) => (
            <button
              key={link.id}
              type="button"
              className="pricing-cta"
              onClick={() => scrollToSection(link.id)}
            >
              {link.label}
            </button>
          ))}
        </div>
      </article>

      {hasAnyError ? <div className="error-box">Hay secciones con errores de carga. Revisa cada bloque para más detalle.</div> : null}

      <div className="stack">
        <div className="summary-grid">
          {summaryLoading
            ? Array.from({ length: 5 }).map((_, index) => (
                <SummarySkeleton key={index} />
              ))
            : profileCards.map((card) => (
                <article key={card.title} className="summary-tile">
                  <small>{card.title}</small>
                  <strong>{card.value}</strong>
                  <span>{card.subtitle}</span>
                </article>
              ))}
        </div>

        <div className="grid-2">
          <article id="student-profile" className="card section-card">
            <h3>Mi Perfil</h3>
            {loadingProfile ? (
              <SectionStatus title="Cargando perfil" description="Obteniendo los datos personales del estudiante." loading />
            ) : profileError ? (
              <div className="error-box">{profileError}</div>
            ) : (
              <dl className="detail-list">
                <div>
                  <dt>Nombre</dt>
                  <dd>{profile?.nombre_completo || profile?.nombre || 'Pendiente'}</dd>
                </div>
                <div>
                  <dt>Correo</dt>
                  <dd>{profile?.email || profile?.correo || 'Pendiente'}</dd>
                </div>
                <div>
                  <dt>RUT</dt>
                  <dd>{profile?.rut || 'Pendiente'}</dd>
                </div>
                <div>
                  <dt>Curso actual</dt>
                  <dd>{profile?.curso_actual || profile?.curso || 'Sin asignar'}</dd>
                </div>
              </dl>
            )}
          </article>

          <article id="student-classes" className="card section-card">
            <h3>Mis Clases</h3>
            {loadingClasses ? (
              <SectionStatus title="Cargando clases" description="Preparando el listado de asignaturas activas." loading />
            ) : classesError ? (
              <div className="error-box">{classesError}</div>
            ) : classes.length ? (
              <ul className="compact-list">
                {classes.slice(0, 6).map((item) => (
                  <li key={item.clase_id || item.id || `${item.curso}-${item.asignatura}`}>
                    <strong>{item.asignatura || item.nombre || 'Asignatura'}</strong>
                    <span>{item.curso || item.curso_nombre || 'Curso no disponible'}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptySection title="Sin clases asignadas" description="Todavía no hay asignaturas registradas para este ciclo." />
            )}
          </article>

          <article id="student-grades" className="card section-card">
            <h3>Mis Notas</h3>
            {loadingGrades ? (
              <SectionStatus title="Cargando notas" description="Consultando las evaluaciones y calificaciones disponibles." loading />
            ) : gradesError ? (
              <div className="error-box">{gradesError}</div>
            ) : grades.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Evaluación</th>
                      <th>Curso</th>
                      <th>Nota</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grades.slice(0, 8).map((item, index) => (
                      <tr key={item.evaluacion_id || item.id || `${item.nombre}-${index}`}>
                        <td>{item.evaluacion || item.nombre || 'Evaluación'}</td>
                        <td>{item.curso || item.clase || 'Curso'}</td>
                        <td>{formatNumber(item.nota ?? item.promedio, '-')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptySection title="Sin notas registradas" description="Cuando existan evaluaciones, aparecerán aquí con su detalle." />
            )}
          </article>

          <article id="student-attendance" className="card section-card">
            <h3>Mi Asistencia</h3>
            {loadingAttendance ? (
              <SectionStatus title="Cargando asistencia" description="Recuperando los registros de asistencia del estudiante." loading />
            ) : attendanceError ? (
              <div className="error-box">{attendanceError}</div>
            ) : attendance.length ? (
              <ul className="compact-list">
                {attendance.slice(0, 8).map((item, index) => (
                  <li key={item.id || item.fecha || index}>
                    <strong>{item.fecha || item.dia || 'Registro'}</strong>
                    <span>{item.estado || item.porcentaje || 'Sin estado'}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptySection title="Sin registros de asistencia" description="Aún no hay asistencia cargada para este periodo." />
            )}
          </article>
        </div>

        <article id="student-history" className="card section-card grid-full">
          <h3>Historial Académico</h3>

          <div className="actions">
            <label>
              Ciclo académico
              <select value={selectedCycle} onChange={(e) => setSelectedCycle(e.target.value)}>
                {(history?.ciclos_disponibles || []).map((ciclo) => (
                  <option key={ciclo.id} value={ciclo.id}>
                    {ciclo.nombre} ({ciclo.estado})
                  </option>
                ))}
              </select>
            </label>
          </div>

          {loadingHistory ? <SectionStatus title="Cargando historial académico" description="Consolidando notas, promedio y asistencia del ciclo." loading /> : null}
          {historyError ? <div className="error-box">{historyError}</div> : null}

          {!loadingHistory && !historyError && history?.ciclo ? (
            <div className="summary-grid section-card">
              <article className="summary-tile">
                <small>Ciclo activo</small>
                <strong>{history.ciclo.nombre}</strong>
                <span>{history.ciclo.estado || 'Activo'}</span>
              </article>
              <article className="summary-tile">
                <small>Asignaturas</small>
                <strong>{(history.asignaturas || []).length}</strong>
                <span>Consolidado del ciclo</span>
              </article>
              <article className="summary-tile">
                <small>Promedio general</small>
                <strong>{historyAverage !== null ? formatNumber(historyAverage, '-') : '-'}</strong>
                <span>Promedio de asignaturas con nota</span>
              </article>
            </div>
          ) : null}

          {!loadingHistory && !historyError && Array.isArray(history?.asignaturas) && history.asignaturas.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Asignatura</th>
                    <th>Curso</th>
                    <th>Promedio</th>
                    <th>Asistencia</th>
                    <th>Notas</th>
                  </tr>
                </thead>
                <tbody>
                  {history.asignaturas.map((item) => (
                    <tr key={item.clase_id}>
                      <td>{item.asignatura}</td>
                      <td>{item.curso}</td>
                      <td>{formatNumber(item.promedio, '-')}</td>
                      <td>{formatPercentage(item.porcentaje_asistencia)}</td>
                      <td>{Array.isArray(item.notas) && item.notas.length ? item.notas.join(', ') : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </article>
      </div>
    </section>
  );
}
