/**
 * Form for creating a new referral (derivacion).
 */
export function ReferralForm({ students, form, saving, canCreateReferral, onChange, onSubmit }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>Nueva derivacion</h3>

      <label>
        Estudiante
        <select
          value={form.estudiante_id}
          onChange={(e) => onChange('estudiante_id', e.target.value)}
          disabled={!canCreateReferral || saving}
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
        Profesional destino
        <input
          value={form.profesional_destino}
          onChange={(e) => onChange('profesional_destino', e.target.value)}
          disabled={!canCreateReferral || saving}
          required
        />
      </label>

      <label>
        Especialidad
        <input
          value={form.especialidad}
          onChange={(e) => onChange('especialidad', e.target.value)}
          disabled={!canCreateReferral || saving}
          required
        />
      </label>

      <label>
        Fecha derivacion
        <input
          type="date"
          value={form.fecha_derivacion}
          onChange={(e) => onChange('fecha_derivacion', e.target.value)}
          disabled={!canCreateReferral || saving}
        />
      </label>

      <label>
        Motivo
        <textarea
          value={form.motivo}
          onChange={(e) => onChange('motivo', e.target.value)}
          disabled={!canCreateReferral || saving}
          required
        />
      </label>

      <div>
        <button
          type="submit"
          disabled={
            !canCreateReferral ||
            saving ||
            !form.estudiante_id ||
            !form.profesional_destino ||
            !form.especialidad ||
            !form.motivo
          }
        >
          {saving ? 'Guardando...' : 'Registrar derivacion'}
        </button>
      </div>
    </form>
  );
}
