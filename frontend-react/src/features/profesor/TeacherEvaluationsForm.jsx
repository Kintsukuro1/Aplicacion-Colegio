/**
 * Form for creating or editing teacher evaluations.
 */
export function TeacherEvaluationsForm({ form, classes, editingId, formLocked, isSaving, canSubmit, onChange, onSubmit, onClose }) {
  return (
    <form className="form-grid" onSubmit={onSubmit} style={{ marginTop: '0', padding: '0', background: 'transparent', boxShadow: 'none' }}>
      
      <label style={{ gridColumn: '1 / -1' }}>
        Clase
        <select value={form.clase} onChange={(e) => onChange('clase', e.target.value)} required disabled={formLocked || isSaving}>
          <option value="">Seleccionar</option>
          {classes.map((row) => (
            <option key={row.id} value={row.id}>
              {row.curso_nombre} - {row.asignatura_nombre}
            </option>
          ))}
        </select>
      </label>

      <label style={{ gridColumn: '1 / -1' }}>
        Nombre
        <input value={form.nombre} onChange={(e) => onChange('nombre', e.target.value)} required disabled={formLocked || isSaving} />
      </label>

      <label>
        Fecha Evaluación
        <input
          type="date"
          value={form.fecha_evaluacion}
          onChange={(e) => onChange('fecha_evaluacion', e.target.value)}
          required
          disabled={formLocked || isSaving}
        />
      </label>

      <label>
        Ponderación (%)
        <input type="number" step="0.1" value={form.ponderacion} onChange={(e) => onChange('ponderacion', e.target.value)} disabled={formLocked || isSaving} />
      </label>

      <label>
        Tipo
        <select value={form.tipo_evaluacion} onChange={(e) => onChange('tipo_evaluacion', e.target.value)} disabled={formLocked || isSaving}>
          <option value="sumativa">Sumativa</option>
          <option value="formativa">Formativa</option>
          <option value="diagnostica">Diagnostica</option>
          <option value="acumulativa">Acumulativa</option>
        </select>
      </label>

      <label>
        Periodo
        <input value={form.periodo} onChange={(e) => onChange('periodo', e.target.value)} disabled={formLocked || isSaving} />
      </label>

      <div className="actions full" style={{ marginTop: '1rem' }}>
        <button type="submit" disabled={!canSubmit || isSaving}>
          {isSaving ? 'Guardando...' : editingId ? 'Actualizar' : 'Crear'}
        </button>
        <button type="button" className="secondary" onClick={onClose} disabled={isSaving}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
