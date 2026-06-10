/**
 * CRUD form for individual attendance records.
 */
const ATTENDANCE_STATES = [
  { value: 'P', label: 'Presente' },
  { value: 'A', label: 'Ausente' },
  { value: 'T', label: 'Tardanza' },
  { value: 'J', label: 'Justificada' },
];

export function AdminAttendanceForm({ classes, form, editingId, saving, canSubmit, onChange, onSubmit, onCancel }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>{editingId ? `Editar asistencia #${editingId}` : 'Nueva Asistencia'}</h3>

      <label>
        Clase
        <select value={form.clase} onChange={(e) => onChange('clase', e.target.value)} required disabled={saving}>
          <option value="">Seleccionar</option>
          {classes.map((row) => (
            <option key={row.id} value={row.id}>
              {row.curso_nombre} - {row.asignatura_nombre}
            </option>
          ))}
        </select>
      </label>

      <label>
        Estudiante ID
        <input
          type="number"
          value={form.estudiante}
          onChange={(e) => onChange('estudiante', e.target.value)}
          min="1"
          required
          disabled={saving}
        />
      </label>

      <label>
        Fecha
        <input type="date" value={form.fecha} onChange={(e) => onChange('fecha', e.target.value)} required disabled={saving} />
      </label>

      <label>
        Estado
        <select value={form.estado} onChange={(e) => onChange('estado', e.target.value)} disabled={saving}>
          {ATTENDANCE_STATES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label>
        Tipo Asistencia
        <input value={form.tipo_asistencia} onChange={(e) => onChange('tipo_asistencia', e.target.value)} disabled={saving} />
      </label>

      <label>
        Observaciones
        <input value={form.observaciones} onChange={(e) => onChange('observaciones', e.target.value)} disabled={saving} />
      </label>

      <div className="actions full">
        <button type="submit" disabled={!canSubmit || saving}>
          {saving ? 'Guardando...' : editingId ? 'Actualizar' : 'Crear'}
        </button>
        {editingId ? (
          <button type="button" className="secondary" onClick={onCancel}>
            Cancelar Edicion
          </button>
        ) : null}
      </div>
    </form>
  );
}
