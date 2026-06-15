/**
 * Form for creating a new library resource.
 */
export function ResourceForm({ form, saving, canCreate, onChange, onSubmit }) {
  return (
    <form className="card section-card form-grid" onSubmit={onSubmit}>
      <h3>Nuevo recurso</h3>

      <label>
        Titulo
        <input
          value={form.titulo}
          onChange={(e) => onChange('titulo', e.target.value)}
          disabled={!canCreate || saving}
          required
        />
      </label>

      <label>
        Descripcion
        <textarea
          value={form.descripcion}
          onChange={(e) => onChange('descripcion', e.target.value)}
          disabled={!canCreate || saving}
        />
      </label>

      <label>
        Tipo
        <select value={form.tipo} onChange={(e) => onChange('tipo', e.target.value)} disabled={!canCreate || saving}>
          <option value="LIBRO">Libro</option>
          <option value="VIDEO">Video</option>
          <option value="DOCUMENTO">Documento</option>
          <option value="ENLACE">Enlace</option>
          <option value="SOFTWARE">Software</option>
          <option value="MATERIAL_CRA">Material CRA</option>
        </select>
      </label>

      <label>
        URL externa
        <input value={form.url_externa} onChange={(e) => onChange('url_externa', e.target.value)} disabled={!canCreate || saving} />
      </label>

      <label>
        <input
          type="checkbox"
          checked={form.publicado}
          onChange={(e) => onChange('publicado', e.target.checked)}
          disabled={!canCreate || saving}
        />
        Publicado
      </label>

      <label>
        <input
          type="checkbox"
          checked={form.es_plan_lector}
          onChange={(e) => onChange('es_plan_lector', e.target.checked)}
          disabled={!canCreate || saving}
        />
        Plan lector
      </label>

      <div>
        <button type="submit" disabled={!canCreate || saving || !form.titulo}>
          {saving ? 'Guardando...' : 'Crear recurso'}
        </button>
      </div>
    </form>
  );
}
