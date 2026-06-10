/**
 * Form for registering student tardiness (atrasos).
 */
export function DelayForm({ students, classes, form, saving, canCreate, onChange, onSubmit }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>Registrar atraso</h3>

      <label>
        Estudiante
        <select
          value={form.estudiante_id}
          onChange={(e) => onChange('estudiante_id', e.target.value)}
          disabled={!canCreate || saving}
          required
        >
          <option value="">Selecciona estudiante</option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>
              {student.nombre_completo || student.nombre || `Estudiante #${student.id}`}
            </option>
          ))}
        </select>
      </label>

      <label>
        Clase
        <select
          value={form.clase_id}
          onChange={(e) => onChange('clase_id', e.target.value)}
          disabled={!canCreate || saving}
          required
        >
          <option value="">Selecciona clase</option>
          {classes.map((item) => (
            <option key={item.id} value={item.id}>
              {item.nombre || item.asignatura || `Clase #${item.id}`}
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
          disabled={!canCreate || saving}
          required
        />
      </label>

      <label>
        Observaciones
        <textarea
          value={form.observaciones}
          onChange={(e) => onChange('observaciones', e.target.value)}
          disabled={!canCreate || saving}
        />
      </label>

      <div>
        <button
          type="submit"
          disabled={!canCreate || saving || !form.estudiante_id || !form.clase_id || !form.fecha}
        >
          {saving ? 'Guardando...' : 'Registrar atraso'}
        </button>
      </div>
    </form>
  );
}
