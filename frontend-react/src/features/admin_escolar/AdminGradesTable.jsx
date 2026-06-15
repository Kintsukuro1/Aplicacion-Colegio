import { formatGrade, normalizeGrade } from '../../utils/formatters';

/**
 * Table displaying grades with selection and row actions.
 */
export function AdminGradesTable({
  rows,
  selectedIds,
  canEdit,
  canDelete,
  processingBulk,
  onToggleSelect,
  onToggleSelectAll,
  onStartEdit,
  onDelete,
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                checked={rows.length > 0 && rows.every((row) => selectedIds.includes(row.id_calificacion))}
                onChange={onToggleSelectAll}
                disabled={!canDelete || rows.length === 0 || processingBulk}
              />
            </th>
            <th>ID</th>
            <th>Evaluacion</th>
            <th>Estudiante</th>
            <th>Nota</th>
            <th>Fecha Creacion</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const normalizedGrade = normalizeGrade(row.nota);
            const isLowGrade = normalizedGrade !== null && normalizedGrade < 4;

            return (
            <tr key={row.id_calificacion}>
              <td>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(row.id_calificacion)}
                  onChange={() => onToggleSelect(row.id_calificacion)}
                  disabled={!canDelete || processingBulk}
                />
              </td>
              <td>{row.id_calificacion}</td>
              <td>{row.evaluacion}</td>
              <td>{row.estudiante_nombre || row.estudiante}</td>
              <td>
                <span className={isLowGrade ? 'grade-low' : undefined}>
                  {formatGrade(row.nota, '-')}
                </span>
              </td>
              <td>{row.fecha_creacion || '-'}</td>
              <td className="actions-cell">
                {canEdit ? (
                  <button type="button" className="small" onClick={() => onStartEdit(row)} disabled={processingBulk}>
                    Editar
                  </button>
                ) : null}
                {canDelete ? (
                  <button type="button" className="small danger" onClick={() => onDelete(row.id_calificacion)} disabled={processingBulk}>
                    Eliminar
                  </button>
                ) : null}
                {!canEdit && !canDelete ? <span>-</span> : null}
              </td>
            </tr>
          );
          })}
          {rows.length === 0 ? (
            <tr>
              <td colSpan="7">Sin registros</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
