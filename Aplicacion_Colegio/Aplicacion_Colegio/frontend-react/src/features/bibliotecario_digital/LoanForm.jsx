/**
 * Form for creating a new book/resource loan.
 */
export function LoanForm({ resources, users, form, saving, canManageLoans, onChange, onSubmit }) {
  return (
    <form className="card section-card form-grid" onSubmit={onSubmit}>
      <h3>Crear prestamo</h3>
      <label>
        Recurso
        <select
          value={form.recurso_id}
          onChange={(e) => onChange('recurso_id', e.target.value)}
          disabled={!canManageLoans || saving}
          required
        >
          <option value="">Selecciona recurso</option>
          {resources.map((item) => (
            <option key={item.id || item.id_recurso} value={item.id || item.id_recurso}>
              {item.titulo || `Recurso #${item.id || item.id_recurso}`}
            </option>
          ))}
        </select>
      </label>

      <label>
        Usuario
        <select
          value={form.usuario_id}
          onChange={(e) => onChange('usuario_id', e.target.value)}
          disabled={!canManageLoans || saving}
          required
        >
          <option value="">Selecciona usuario</option>
          {users.map((item) => (
            <option key={item.id} value={item.id}>
              {item.nombre || item.full_name || `Usuario #${item.id}`}
            </option>
          ))}
        </select>
      </label>

      <label>
        Dias prestamo
        <input
          type="number"
          min="1"
          max="90"
          value={form.dias_prestamo}
          onChange={(e) => onChange('dias_prestamo', e.target.value)}
          disabled={!canManageLoans || saving}
        />
      </label>

      <div>
        <button type="submit" disabled={!canManageLoans || saving || !form.recurso_id || !form.usuario_id}>
          {saving ? 'Guardando...' : 'Registrar prestamo'}
        </button>
      </div>
    </form>
  );
}
