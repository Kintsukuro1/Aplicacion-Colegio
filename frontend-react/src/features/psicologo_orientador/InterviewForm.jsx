/**
 * Form for registering a new student interview.
 */
export function InterviewForm({ students, form, saving, canCreate, onChange, onSubmit }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>Nueva entrevista</h3>

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
        Motivo
        <select value={form.motivo} onChange={(e) => onChange('motivo', e.target.value)} disabled={!canCreate || saving}>
          <option value="ACADEMICO">Academico</option>
          <option value="CONDUCTUAL">Conductual</option>
          <option value="SOCIOEMOCIONAL">Socioemocional</option>
          <option value="FAMILIAR">Familiar</option>
          <option value="OTRO">Otro</option>
        </select>
      </label>

      <label>
        Observaciones
        <textarea
          value={form.observaciones}
          onChange={(e) => onChange('observaciones', e.target.value)}
          disabled={!canCreate || saving}
          required
        />
      </label>

      <label>
        Acuerdos
        <textarea value={form.acuerdos} onChange={(e) => onChange('acuerdos', e.target.value)} disabled={!canCreate || saving} />
      </label>

      <label>
        <input
          type="checkbox"
          checked={form.seguimiento_requerido}
          onChange={(e) => onChange('seguimiento_requerido', e.target.checked)}
          disabled={!canCreate || saving}
        />
        Requiere seguimiento
      </label>

      <div>
        <button type="submit" disabled={!canCreate || saving || !form.estudiante_id || !form.fecha || !form.observaciones}>
          {saving ? 'Guardando...' : 'Registrar entrevista'}
        </button>
      </div>
    </form>
  );
}
