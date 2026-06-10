/**
 * Attendance table with selection checkboxes and row actions.
 */
export function AdminAttendanceTable({
  rows,
  selectedIds,
  canEdit,
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
                checked={rows.length > 0 && rows.every((row) => selectedIds.includes(row.id_asistencia))}
                onChange={onToggleSelectAll}
                disabled={!canEdit || rows.length === 0 || processingBulk}
              />
            </th>
            <th>ID</th>
            <th>Clase</th>
            <th>Estudiante</th>
            <th>Fecha</th>
            <th>Estado</th>
            <th>Tipo</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id_asistencia}>
              <td>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(row.id_asistencia)}
                  onChange={() => onToggleSelect(row.id_asistencia)}
                  disabled={!canEdit || processingBulk}
                />
              </td>
              <td>{row.id_asistencia}</td>
              <td>{row.clase}</td>
              <td>{row.estudiante_nombre || row.estudiante}</td>
              <td>{row.fecha}</td>
              <td>{row.estado}</td>
              <td>{row.tipo_asistencia || '-'}</td>
              <td className="actions-cell">
                {canEdit ? (
                  <button type="button" className="small" onClick={() => onStartEdit(row)}>
                    Editar
                  </button>
                ) : null}
                {canEdit ? (
                  <button type="button" className="small danger" onClick={() => onDelete(row.id_asistencia)}>
                    Eliminar
                  </button>
                ) : null}
                {!canEdit ? <span>-</span> : null}
              </td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan="8">Sin registros</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
