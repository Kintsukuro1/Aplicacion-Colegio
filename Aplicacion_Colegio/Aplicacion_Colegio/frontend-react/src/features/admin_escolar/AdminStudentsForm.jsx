/**
 * Form for creating or editing students.
 */
export function AdminStudentsForm({ form, editingId, formLocked, saving, formError, canSubmit, onChange, resetForm, onSubmit }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>{editingId ? `Editar #${editingId}` : 'Nuevo Estudiante'}</h3>

      {formError ? (
        <div className="error-box" role="alert" aria-live="assertive">
          {formError}
        </div>
      ) : null}

      <label>
        Email
        <input value={form.email} onChange={(e) => onChange('email', e.target.value)} required disabled={formLocked} />
      </label>

      <label>
        RUT
        <input value={form.rut} onChange={(e) => onChange('rut', e.target.value)} required disabled={formLocked} />
      </label>

      <label>
        Nombre
        <input value={form.nombre} onChange={(e) => onChange('nombre', e.target.value)} required disabled={formLocked} />
      </label>

      <label>
        Apellido Paterno
        <input
          value={form.apellido_paterno}
          onChange={(e) => onChange('apellido_paterno', e.target.value)}
          required
          disabled={formLocked}
        />
      </label>

      <label>
        Apellido Materno
        <input
          value={form.apellido_materno}
          onChange={(e) => onChange('apellido_materno', e.target.value)}
          disabled={formLocked}
        />
      </label>

      <label>
        Activo
        <select
          value={form.is_active ? '1' : '0'}
          onChange={(e) => onChange('is_active', e.target.value === '1')}
          disabled={formLocked}
        >
          <option value="1">Si</option>
          <option value="0">No</option>
        </select>
      </label>

      <div className="actions full">
        <button type="submit" disabled={!canSubmit || saving || formLocked}>
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
