/**
 * Form for updating an existing referral (derivacion).
 */
export function UpdateReferralForm({ form, saving, canEditReferral, onChange, onSubmit }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>Actualizar derivacion</h3>

      <label>
        Derivacion ID
        <input
          type="number"
          min="1"
          value={form.derivacion_id}
          onChange={(e) => onChange('derivacion_id', e.target.value)}
          disabled={!canEditReferral || saving}
          required
        />
      </label>

      <label>
        Estado
        <select
          value={form.estado}
          onChange={(e) => onChange('estado', e.target.value)}
          disabled={!canEditReferral || saving}
        >
          <option value="PENDIENTE">Pendiente</option>
          <option value="EN_PROCESO">En proceso</option>
          <option value="COMPLETADA">Completada</option>
          <option value="CANCELADA">Cancelada</option>
        </select>
      </label>

      <label>
        Fecha retorno
        <input
          type="date"
          value={form.fecha_retorno}
          onChange={(e) => onChange('fecha_retorno', e.target.value)}
          disabled={!canEditReferral || saving}
        />
      </label>

      <label>
        Informe retorno
        <textarea
          value={form.informe_retorno}
          onChange={(e) => onChange('informe_retorno', e.target.value)}
          disabled={!canEditReferral || saving}
        />
      </label>

      <div>
        <button type="submit" disabled={!canEditReferral || saving || !form.derivacion_id}>
          {saving ? 'Guardando...' : 'Actualizar derivacion'}
        </button>
      </div>
    </form>
  );
}
