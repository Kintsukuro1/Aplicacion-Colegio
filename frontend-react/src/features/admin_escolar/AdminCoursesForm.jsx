/**
 * Form for creating or editing courses.
 */
export function AdminCoursesForm({ form, editingId, formLocked, isSaving, canSubmit, onChange, onSubmit, onClose }) {
  return (
    <form className="form-grid" onSubmit={onSubmit} style={{ marginTop: '0', padding: '0', background: 'transparent', boxShadow: 'none' }}>
      <label style={{ gridColumn: '1 / -1' }}>
        Nombre
        <input
          value={form.nombre}
          onChange={(e) => onChange('nombre', e.target.value)}
          required
          disabled={formLocked || isSaving}
        />
      </label>

      <label>
        Nivel ID
        <input
          type="number"
          value={form.nivel_id}
          onChange={(e) => onChange('nivel_id', e.target.value)}
          required
          disabled={formLocked || isSaving}
          min="1"
        />
      </label>

      <label>
        Ciclo Academico ID (opcional)
        <input
          type="number"
          value={form.ciclo_academico_id}
          onChange={(e) => onChange('ciclo_academico_id', e.target.value)}
          disabled={formLocked || isSaving}
          min="1"
        />
      </label>

      <label>
        Activo
        <select
          value={form.activo ? '1' : '0'}
          onChange={(e) => onChange('activo', e.target.value === '1')}
          disabled={formLocked || isSaving}
        >
          <option value="1">Si</option>
          <option value="0">No</option>
        </select>
      </label>

      <div className="actions full" style={{ marginTop: '1rem' }}>
        <button type="submit" disabled={!canSubmit || formLocked || isSaving}>
          {isSaving ? 'Guardando...' : editingId ? 'Actualizar' : 'Crear'}
        </button>
        <button type="button" className="secondary" onClick={onClose} disabled={isSaving}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
