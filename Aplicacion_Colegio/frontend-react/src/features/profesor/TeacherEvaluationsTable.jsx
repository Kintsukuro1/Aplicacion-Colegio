import { formatNumber } from '../../utils/formatters';

/**
 * Table displaying teacher evaluations.
 */
export function TeacherEvaluationsTable({ rows, canEdit, canDelete, isDeleting, onStartEdit, onDelete }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Fecha</th>
            <th>Ponderación</th>
            <th>Tipo</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id_evaluacion}>
              <td>{row.id_evaluacion}</td>
              <td>{row.nombre}</td>
              <td>{row.fecha_evaluacion}</td>
              <td>{formatNumber(row.ponderacion)}%</td>
              <td>{row.tipo_evaluacion}</td>
              <td className="actions-cell">
                {canEdit ? (
                  <button type="button" className="small" onClick={() => onStartEdit(row)}>
                    Editar
                  </button>
                ) : null}
                {canDelete ? (
                  <button type="button" className="small danger" onClick={() => onDelete(row.id_evaluacion)} disabled={isDeleting}>
                    Eliminar
                  </button>
                ) : null}
                {!canEdit && !canDelete ? <span>Solo lectura</span> : null}
              </td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan="6">Sin registros</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
