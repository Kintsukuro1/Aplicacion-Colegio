/**
 * Form for reviewing absence justifications.
 */
export function ReviewForm({ form, saving, canReview, onChange, onSubmit }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>Revisar justificativo</h3>

      <label>
        Justificativo ID
        <input
          type="number"
          min="1"
          value={form.justificativo_id}
          onChange={(e) => onChange('justificativo_id', e.target.value)}
          disabled={!canReview || saving}
          required
        />
      </label>

      <label>
        Estado
        <select
          value={form.estado}
          onChange={(e) => onChange('estado', e.target.value)}
          disabled={!canReview || saving}
        >
          <option value="APROBADO">Aprobado</option>
          <option value="RECHAZADO">Rechazado</option>
        </select>
      </label>

      <label>
        Observaciones
        <textarea
          value={form.observaciones}
          onChange={(e) => onChange('observaciones', e.target.value)}
          disabled={!canReview || saving}
        />
      </label>

      <div>
        <button type="submit" disabled={!canReview || saving || !form.justificativo_id}>
          {saving ? 'Guardando...' : 'Actualizar justificativo'}
        </button>
      </div>
    </form>
  );
}
