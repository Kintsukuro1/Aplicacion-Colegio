/**
 * Form for updating PIE (Programa de Integracion Escolar) status.
 */
export function PieForm({ students, form, saving, canCreate, onChange, onSubmit }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>Actualizar estado PIE</h3>

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
        <input
          type="checkbox"
          checked={form.requiere_pie}
          onChange={(e) => onChange('requiere_pie', e.target.checked)}
          disabled={!canCreate || saving}
        />
        Requiere PIE
      </label>

      <div>
        <button type="submit" disabled={!canCreate || saving || !form.estudiante_id}>
          {saving ? 'Guardando...' : 'Actualizar PIE'}
        </button>
      </div>
    </form>
  );
}
