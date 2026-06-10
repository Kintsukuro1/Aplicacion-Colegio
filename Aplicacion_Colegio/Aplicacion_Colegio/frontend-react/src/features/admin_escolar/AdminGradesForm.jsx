/**
 * Form for creating or editing grades.
 */
export function AdminGradesForm({ form, editingId, formLocked, saving, canSubmit, onChange, onCancel, onSubmit }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>{editingId ? `Editar calificacion #${editingId}` : 'Nueva Calificacion'}</h3>

      <label>
        Evaluacion ID
        <input
          type="number"
          value={form.evaluacion}
          onChange={(e) => onChange('evaluacion', e.target.value)}
          required
          disabled={formLocked || saving}
          min="1"
        />
      </label>

      <label>
        Estudiante ID
        <input
          type="number"
          value={form.estudiante}
          onChange={(e) => onChange('estudiante', e.target.value)}
          required
          disabled={formLocked || saving}
          min="1"
        />
      </label>

      <label>
        Nota
        <input
          type="number"
          step="0.1"
          value={form.nota}
          onChange={(e) => onChange('nota', e.target.value)}
          required
          disabled={formLocked || saving}
          min="1"
          max="7"
        />
      </label>

      <div className="actions full">
        <button type="submit" disabled={!canSubmit || formLocked || saving}>
          {saving ? 'Guardando...' : editingId ? 'Actualizar' : 'Crear'}
        </button>
        {editingId ? (
          <button type="button" className="secondary" onClick={onCancel} disabled={saving}>
            Cancelar Edicion
          </button>
        ) : null}
      </div>
    </form>
  );
}
