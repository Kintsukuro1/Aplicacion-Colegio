/**
 * Form for registering the return of a loan.
 */
export function ReturnForm({ form, saving, canManageLoans, onChange, onSubmit }) {
  return (
    <form className="card section-card form-grid" onSubmit={onSubmit}>
      <h3>Registrar devolucion</h3>
      <label>
        Prestamo ID
        <input
          type="number"
          min="1"
          value={form.prestamo_id}
          onChange={(e) => onChange('prestamo_id', e.target.value)}
          disabled={!canManageLoans || saving}
          required
        />
      </label>
      <div>
        <button type="submit" disabled={!canManageLoans || saving || !form.prestamo_id}>
          {saving ? 'Guardando...' : 'Registrar devolucion'}
        </button>
      </div>
    </form>
  );
}
