import { lazy, Suspense, useMemo } from 'react';
import { SectionStatus, EmptySection } from './StudentSelfCommon';
import { formatGrade, normalizeGrade } from '../../utils/formatters';

const GradesChart = lazy(() => import('./GradesChart'));

export function StudentGradesTab({ grades, loading, error }) {
  const chartData = useMemo(() => {
    if (!grades || grades.length === 0) return null;

    const sortedGrades = grades.toSorted((a, b) => {
      const dateA = new Date(a.fecha_evaluacion || a.fecha_creacion || 0);
      const dateB = new Date(b.fecha_evaluacion || b.fecha_creacion || 0);
      return dateA - dateB;
    });

    const labels = sortedGrades.map((g, i) => g.evaluacion_nombre || g.evaluacion || g.nombre || `Nota ${i + 1}`);
    const data = sortedGrades.map((g) => normalizeGrade(g.nota ?? g.promedio));

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
          pointBackgroundColor: '#2563eb',
        }
      ]
    };
  }, [grades]);

  return (
    <article className="card section-card">
      <h3>Mis Notas</h3>
      {loading ? (
        <SectionStatus title="Cargando notas" description="Consultando las evaluaciones y calificaciones disponibles." loading />
      ) : error ? (
        <div className="error-box" role="alert" aria-live="assertive">{error}</div>
      ) : grades?.length ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {chartData && (
            <Suspense fallback={<div style={{ height: '300px', display: 'grid', placeItems: 'center', color: 'var(--muted)' }}>Cargando gráfico…</div>}>
              <GradesChart chartData={chartData} />
            </Suspense>
          )}
          
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
                {grades.map((item, index) => {
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
        </div>
      ) : (
        <EmptySection title="Sin notas registradas" description="Cuando existan evaluaciones, aparecerán aquí con su detalle." />
      )}
    </article>
  );
}
