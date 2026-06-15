/**
 * Table displaying courses with edit and delete actions.
 */
export function AdminCoursesTable({ rows, canUpdate, canDelete, onStartEdit, onDelete, deletePending }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Nombre</th>
            <th>Activo</th>
            <th>Colegio</th>
            <th>Nivel</th>
            <th>Ciclo</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id_curso}>
              <td>{row.id_curso}</td>
              <td>{row.nombre}</td>
              <td>{row.activo ? 'Si' : 'No'}</td>
              <td>{row.colegio_id ?? '-'}</td>
              <td>{row.nivel_id ?? '-'}</td>
              <td>{row.ciclo_academico_id ?? '-'}</td>
              <td className="actions-cell">
                {canUpdate ? (
                  <button type="button" className="small" onClick={() => onStartEdit(row)}>
                    Editar
                  </button>
                ) : null}
                {canDelete ? (
                  <button type="button" className="small danger" onClick={() => onDelete(row.id_curso)} disabled={deletePending}>
                    Eliminar
                  </button>
                ) : null}
                {!canUpdate && !canDelete ? <span>-</span> : null}
              </td>
            </tr>
          ))}
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
