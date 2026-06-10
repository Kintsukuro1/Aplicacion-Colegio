import { lazy, Suspense, useMemo, useState } from 'react';
import { SectionStatus, EmptySection } from './StudentSelfCommon';
import { formatGrade, normalizeGrade } from '../../utils/formatters';

const GradesChart = lazy(() => import('./GradesChart'));

export function StudentGradesTab({ grades, loading, error, classes = [] }) {
  const [selectedClassId, setSelectedClassId] = useState('');

  const classOptions = useMemo(() => {
    if (!classes?.length) return [];
    return classes.map((item) => ({
      id: String(item.clase_id || item.id_clase_estudiante || item.id || ''),
      label: `${item.asignatura_nombre || item.asignatura || 'Asignatura'} - ${item.curso_nombre || item.curso || 'Curso'}`,
    })).filter((item) => item.id);
  }, [classes]);

  const filteredGrades = useMemo(() => {
    if (!selectedClassId) return grades;
    return (grades || []).filter((item) => String(item.clase_id || item.clase || '') === selectedClassId);
  }, [grades, selectedClassId]);

  const chartData = useMemo(() => {
    if (!filteredGrades || filteredGrades.length === 0) return null;

    const sortedGrades = filteredGrades.toSorted((a, b) => {
      const dateA = new Date(a.fecha_evaluacion || a.fecha_creacion || 0);
      const dateB = new Date(b.fecha_evaluacion || b.fecha_creacion || 0);
      return dateA - dateB;
    });

    const labels = sortedGrades.map((g, i) => g.evaluacion_nombre || g.evaluacion || g.nombre || `Nota ${i + 1}`);
    const data = sortedGrades.map((g) => normalizeGrade(g.nota ?? g.promedio));
    const pointColors = data.map((value) => (value !== null && value < 4 ? '#ef4444' : '#2563eb'));

    return {
      labels,
      datasets: [
        {
          label: 'Evolución de Notas',
          data,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.3,
          fill: true,
          pointBackgroundColor: pointColors,
          pointBorderColor: pointColors,
          segment: {
            borderColor: (ctx) => {
              const value = ctx.p1?.parsed?.y;
              return value !== null && value < 4 ? '#ef4444' : '#3b82f6';
            },
          },
        }
      ]
    };
  }, [filteredGrades]);

  return (
    <article className="card section-card">
      <h3>Mis Notas</h3>
      {loading ? (
        <SectionStatus title="Cargando notas" description="Consultando las evaluaciones y calificaciones disponibles." loading />
      ) : error ? (
        <div className="error-box" role="alert" aria-live="assertive">{error}</div>
      ) : grades?.length ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {classOptions.length ? (
            <label style={{ maxWidth: '420px' }}>
              Curso / Asignatura
              <select value={selectedClassId} onChange={(event) => setSelectedClassId(event.target.value)}>
                <option value="">Todas</option>
                {classOptions.map((item) => (
                  <option key={item.id} value={item.id}>{item.label}</option>
                ))}
              </select>
            </label>
          ) : null}
          {chartData && (
            <Suspense fallback={<div style={{ height: '300px', display: 'grid', placeItems: 'center', color: 'var(--muted)' }}>Cargando gráfico…</div>}>
              <GradesChart chartData={chartData} />
            </Suspense>
          )}
          
          {filteredGrades.length === 0 ? (
            <EmptySection title="Sin notas para este curso" description="Selecciona otra asignatura o vuelve a ver todas las notas." />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Evaluación</th>
                    <th>Fecha</th>
                    <th>Nota</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredGrades.map((item, index) => {
                    const normalizedGrade = normalizeGrade(item.nota ?? item.promedio);
                    const isLowGrade = normalizedGrade !== null && normalizedGrade < 4;

                    return (
                      <tr key={item.id_calificacion || item.evaluacion_id || item.id || `${item.nombre}-${index}`}>
                        <td>{item.evaluacion_nombre || item.evaluacion || item.nombre || 'Evaluación'}</td>
                        <td>{item.fecha_evaluacion || item.fecha_creacion || '-'}</td>
                        <td>
                          <strong className={isLowGrade ? 'grade-low' : undefined}>
                            {formatGrade(item.nota ?? item.promedio, '-')}
                          </strong>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <EmptySection title={selectedClassId ? 'Sin notas para este curso' : 'Sin notas registradas'} description="Cuando existan evaluaciones, aparecerán aquí con su detalle." />
      )}
    </article>
  );
}
