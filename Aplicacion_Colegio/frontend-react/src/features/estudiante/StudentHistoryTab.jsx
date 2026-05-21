import { SectionStatus } from './StudentSelfCommon';
import { formatGrade } from '../../lib/formatters';

export function StudentHistoryTab({ history, loading, error, selectedCycle, onCycleChange, historyAverage, formatPercentage }) {
  return (
    <article className="card section-card grid-full">
      <h3>Historial Académico</h3>

      <div className="actions">
        <label>
          Ciclo académico
          <select value={selectedCycle} onChange={(e) => onCycleChange(e.target.value)}>
            {(history?.ciclos_disponibles || []).map((ciclo) => (
              <option key={ciclo.id} value={ciclo.id}>
                {ciclo.nombre} ({ciclo.estado})
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading ? <SectionStatus title="Cargando historial" description="Consolidando notas, promedio y asistencia del ciclo." loading /> : null}
      {error ? <div className="error-box" role="alert" aria-live="assertive">{error}</div> : null}

      {!loading && !error && history?.ciclo ? (
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
            <strong>{historyAverage !== null ? formatGrade(historyAverage, '-') : '-'}</strong>
            <span>Promedio de asignaturas</span>
          </article>
        </div>
      ) : null}

      {!loading && !error && Array.isArray(history?.asignaturas) && history.asignaturas.length ? (
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
                  <td>{formatGrade(item.promedio, '-')}</td>
                  <td>{formatPercentage(item.porcentaje_asistencia)}</td>
                  <td>
                    {Array.isArray(item.notas) && item.notas.length
                      ? item.notas.map((nota) => formatGrade(nota, '-')).join(' | ')
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </article>
  );
}
