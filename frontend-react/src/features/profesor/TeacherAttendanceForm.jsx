/**
 * Form for creating or editing teacher attendance records.
 */
export function TeacherAttendanceForm({ form, classes, students, editingId, saving, canSubmit, canTakeAttendance, onChange, resetForm, onSubmit }) {
  return (
    <form className="card section-card form-grid" onSubmit={onSubmit}>
      <h3>{editingId ? `Editar #${editingId}` : 'Nueva Asistencia'}</h3>

      <label>
        Clase
        <select
          value={form.clase}
          onChange={(e) => onChange('clase', e.target.value)}
          required
          disabled={!canTakeAttendance}
        >
          <option value="">Seleccionar</option>
          {classes.map((row) => (
            <option key={row.id} value={row.id}>
              {row.curso_nombre} - {row.asignatura_nombre}
            </option>
          ))}
        </select>
      </label>

      <label>
        Estudiante
        <select
          value={form.estudiante}
          onChange={(e) => onChange('estudiante', e.target.value)}
          required
          disabled={!canTakeAttendance}
        >
          <option value="">Seleccionar</option>
          {students.map((row) => (
            <option key={row.id} value={row.id}>
              {row.nombre} {row.apellido_paterno}
            </option>
          ))}
        </select>
      </label>

      <label>
        Fecha
        <input
          type="date"
          value={form.fecha}
          onChange={(e) => onChange('fecha', e.target.value)}
          required
          disabled={!canTakeAttendance}
        />
      </label>

      <label>
        Estado
        <select
          value={form.estado}
          onChange={(e) => onChange('estado', e.target.value)}
          required
          disabled={!canTakeAttendance}
        >
          <option value="P">Presente</option>
          <option value="A">Ausente</option>
          <option value="T">Tardanza</option>
          <option value="J">Justificada</option>
        </select>
      </label>

      <label>
        Tipo
        <select
          value={form.tipo_asistencia}
          onChange={(e) => onChange('tipo_asistencia', e.target.value)}
          disabled={!canTakeAttendance}
        >
          <option value="Presencial">Presencial</option>
          <option value="Remota">Remota</option>
          <option value="Hibrida">Híbrida</option>
        </select>
      </label>

      <label className="full">
        Observaciones
        <input
          value={form.observaciones}
          onChange={(e) => onChange('observaciones', e.target.value)}
          disabled={!canTakeAttendance}
        />
      </label>

      <div className="actions full">
        <button type="submit" disabled={!canSubmit || saving}>
          {saving ? 'Guardando...' : editingId ? 'Actualizar' : 'Crear'}
        </button>
        {editingId ? (
          <button type="button" className="secondary" onClick={resetForm}>
            Cancelar Edicion
          </button>
        ) : null}
      </div>
    </form>
  );
}
