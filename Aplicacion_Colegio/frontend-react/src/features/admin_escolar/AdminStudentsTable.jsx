import { normalizeGrade } from '../../utils/formatters';

/**
 * Table displaying students with selection and row actions.
 */
export function AdminStudentsTable({ rows, selectedIds, canUpdate, canDelete, onToggleSelect, onToggleSelectAll, onStartEdit, onDelete }) {
  const LOW_GRADE_THRESHOLD = 4;
  const LOW_ATTENDANCE_THRESHOLD = 85;

  function buildAlerts(row) {
    const alerts = [];

    const hasNee = Boolean(row?.tiene_nee ?? row?.perfil?.tiene_nee);
    if (hasNee) {
      alerts.push({ label: 'NEE', className: 'badge-warning', title: row?.tipo_nee || row?.perfil?.tipo_nee || 'Necesidades especiales' });
    }

    const gradeValue = normalizeGrade(
      row?.promedio_notas ?? row?.promedio_general ?? row?.promedio
    );
    if (gradeValue !== null && gradeValue < LOW_GRADE_THRESHOLD) {
      alerts.push({ label: 'Bajo 4,0', className: 'badge-danger', title: 'Promedio bajo de rendimiento' });
    }

    const attendanceValue = Number(
      row?.porcentaje_asistencia ?? row?.asistencia_promedio ?? row?.asistencia
    );
    const hasLowAttendance = Number.isFinite(attendanceValue) && attendanceValue > 0 && attendanceValue < LOW_ATTENDANCE_THRESHOLD;

    const estadoAcademico = String(row?.estado_academico || row?.estado || '').toLowerCase();
    const hasRepitencia = estadoAcademico.includes('repit');

    if (hasLowAttendance || hasRepitencia) {
      alerts.push({ label: 'Repitencia', className: 'badge-danger', title: 'Riesgo por notas o asistencia' });
    }

    return alerts;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                checked={rows.length > 0 && rows.every((row) => selectedIds.includes(row.id))}
                onChange={onToggleSelectAll}
                disabled={!canDelete || rows.length === 0}
                aria-label={rows.length > 0 ? 'Seleccionar todos los estudiantes de la pagina' : 'Seleccionar todos'}
              />
            </th>
            <th>ID</th>
            <th>Nombre</th>
            <th>Email</th>
            <th>RUT</th>
            <th>Alertas</th>
            <th>Activo</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const alerts = buildAlerts(row);
            
            let rowClass = '';
            if (alerts.some(a => a.label === 'NEE')) {
              rowClass = 'row-nee';
            } else if (alerts.some(a => a.label === 'Repitencia')) {
              rowClass = 'row-repitencia';
            } else if (alerts.some(a => a.label === 'Bajo 4,0')) {
              rowClass = 'row-low-grade';
            }

            return (
            <tr key={row.id} className={rowClass || undefined}>
              <td>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(row.id)}
                  onChange={() => onToggleSelect(row.id)}
                  disabled={!canDelete}
                  aria-label={`Seleccionar estudiante ${`${row.nombre} ${row.apellido_paterno || ''}`.trim()}`}
                />
              </td>
              <td>{row.id}</td>
              <td>{`${row.nombre} ${row.apellido_paterno || ''}`.trim()}</td>
              <td>{row.email}</td>
              <td>{row.rut}</td>
              <td>
                {alerts.length ? (
                  <div className="badge-row compact">
                    {alerts.map((alert) => (
                      <span key={alert.label} className={`badge ${alert.className}`} title={alert.title}>
                        {alert.label}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span>-</span>
                )}
              </td>
              <td>{row.is_active ? <span className="badge badge-active">Activo</span> : <span className="badge badge-inactive">Inactivo</span>}</td>
              <td className="actions-cell">
                {canUpdate ? (
                  <>
                    <button type="button" className="small" onClick={() => onStartEdit(row)}>
                      Editar
                    </button>
                  </>
                ) : null}
                {canDelete ? (
                  <button type="button" className="small danger" onClick={() => onDelete(row.id)}>
                    Desactivar
                  </button>
                ) : null}
                {!canUpdate && !canDelete ? <span>-</span> : null}
              </td>
            </tr>
          );
          })}
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
