/**
 * Form for creating discipline annotations.
 */
export function AnotacionForm({ students, form, saving, canCreate, onChange, onSubmit }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>Nueva anotacion</h3>

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
        Tipo
        <select value={form.tipo} onChange={(e) => onChange('tipo', e.target.value)} disabled={!canCreate || saving}>
          <option value="POSITIVA">Positiva</option>
          <option value="NEUTRA">Neutra</option>
          <option value="NEGATIVA">Negativa</option>
        </select>
      </label>

      <label>
        Categoria
        <input
          value={form.categoria}
          onChange={(e) => onChange('categoria', e.target.value)}
          disabled={!canCreate || saving}
        />
      </label>

      <label>
        Gravedad
        <input
          type="number"
          min="1"
          max="5"
          value={form.gravedad}
          onChange={(e) => onChange('gravedad', e.target.value)}
          disabled={!canCreate || saving}
        />
      </label>

      <label>
        Descripcion
        <textarea
          value={form.descripcion}
          onChange={(e) => onChange('descripcion', e.target.value)}
          disabled={!canCreate || saving}
          required
        />
      </label>

      <div>
        <button type="submit" disabled={!canCreate || saving || !form.estudiante_id || !form.descripcion}>
          {saving ? 'Guardando...' : 'Registrar anotacion'}
        </button>
      </div>
    </form>
  );
}
