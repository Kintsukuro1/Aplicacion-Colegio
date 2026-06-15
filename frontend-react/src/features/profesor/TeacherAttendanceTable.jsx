/**
 * Table displaying teacher attendance records.
 */
export function TeacherAttendanceTable({ rows, canTakeAttendance, onStartEdit, onDelete }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Fecha</th>
            <th>Estudiante</th>
            <th>Estado</th>
            <th>Tipo</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id_asistencia}>
              <td>{row.id_asistencia}</td>
              <td>{row.fecha}</td>
              <td>{row.estudiante_nombre}</td>
              <td>{row.estado}</td>
              <td>{row.tipo_asistencia}</td>
              <td className="actions-cell">
                {canTakeAttendance ? (
                  <>
                    <button type="button" className="small" onClick={() => onStartEdit(row)}>
                      Editar
                    </button>
                    <button type="button" className="small danger" onClick={() => onDelete(row.id_asistencia)}>
                      Eliminar
                    </button>
                  </>
                ) : (
                  <span>Solo lectura</span>
                )}
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
