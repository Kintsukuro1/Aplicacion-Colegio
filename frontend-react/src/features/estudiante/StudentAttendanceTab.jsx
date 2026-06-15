import { lazy, Suspense, useMemo } from 'react';
import { SectionStatus, EmptySection } from './StudentSelfCommon';

const AttendanceChart = lazy(() => import('./AttendanceChart'));

const STATE_COLORS = {
  P: '#10b981',
  A: '#ef4444',
  J: '#3b82f6',
  T: '#f59e0b',
};

const STATE_LABELS = {
  P: 'Presente',
  A: 'Ausente',
  J: 'Justificado',
  T: 'Atraso',
};

export function StudentAttendanceTab({ attendance, loading, error }) {
  const chartData = useMemo(() => {
    if (!attendance || attendance.length === 0) return null;

    const counts = { P: 0, A: 0, J: 0, T: 0 };
    let otherCount = 0;

    attendance.forEach(item => {
      const estado = item.estado || 'P';
      const key = estado.toString().toUpperCase().charAt(0);
      
      if (counts[key] !== undefined) {
        counts[key]++;
      } else {
        otherCount++;
      }
    });

    const labels = [];
    const data = [];
    const backgroundColor = [];

    Object.entries(counts).forEach(([key, value]) => {
      if (value > 0) {
        labels.push(STATE_LABELS[key]);
        data.push(value);
        backgroundColor.push(STATE_COLORS[key]);
      }
    });

    if (otherCount > 0) {
      labels.push('Otro');
      data.push(otherCount);
      backgroundColor.push('#888888');
    }

    return {
      labels,
      datasets: [
        {
          data,
          backgroundColor,
          borderWidth: 1,
        },
      ],
    };
  }, [attendance]);

  const attendanceByClass = useMemo(() => {
    if (!attendance || attendance.length === 0) return [];

    const groups = new Map();

    attendance.forEach((item) => {
      const classId = item.clase_id || `${item.curso_nombre}-${item.asignatura_nombre}`;
      const current = groups.get(classId) || {
        id: classId,
        curso: item.curso_nombre || 'Curso',
        asignatura: item.asignatura_nombre || 'Asignatura',
        P: 0,
        A: 0,
        J: 0,
        T: 0,
        total: 0,
      };

      const estado = (item.estado || 'P').toString().toUpperCase().charAt(0);
      if (current[estado] !== undefined) {
        current[estado] += 1;
      }
      current.total += 1;
      groups.set(classId, current);
    });

    return Array.from(groups.values());
  }, [attendance]);

  const totalClasses = attendance?.length || 0;

  return (
    <article className="card section-card">
      <h3>Mi Asistencia</h3>
      {loading ? (
        <SectionStatus title="Cargando asistencia" description="Recuperando los registros de asistencia del estudiante." loading />
      ) : error ? (
        <div className="error-box" role="alert" aria-live="assertive">{error}</div>
      ) : chartData ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem', padding: '1rem 0' }}>
          <Suspense fallback={<div style={{ height: '300px', display: 'grid', placeItems: 'center', color: 'var(--muted)' }}>Cargando gráfico…</div>}>
            <AttendanceChart chartData={chartData} totalClasses={totalClasses} />
          </Suspense>
          <div style={{ textAlign: 'center' }}>
            <p style={{ margin: 0, color: 'var(--muted)' }}>
              Total de registros: <strong>{totalClasses}</strong>
            </p>
          </div>
          {attendanceByClass.length ? (
            <div className="table-wrap" style={{ width: '100%' }}>
              <table>
                <thead>
                  <tr>
                    <th>Asignatura</th>
                    <th>Curso</th>
                    <th>Presente</th>
                    <th>Ausente</th>
                    <th>Justificado</th>
                    <th>Atraso</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {attendanceByClass.map((item) => (
                    <tr key={item.id}>
                      <td>{item.asignatura}</td>
                      <td>{item.curso}</td>
                      <td>{item.P}</td>
                      <td>{item.A}</td>
                      <td>{item.J}</td>
                      <td>{item.T}</td>
                      <td>{item.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : (
        <EmptySection title="Sin registros de asistencia" description="Aún no hay asistencia cargada para este periodo." />
      )}
    </article>
  );
}
