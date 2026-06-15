/**
 * Form for publishing or unpublishing a library resource.
 */
export function PublishForm({ resources, form, saving, canEdit, onChange, onSubmit }) {
  return (
    <form className="card section-card form-grid" onSubmit={onSubmit}>
      <h3>Publicar o despublicar recurso</h3>
      <label>
        Recurso
        <select
          value={form.recurso_id}
          onChange={(e) => onChange('recurso_id', e.target.value)}
          disabled={!canEdit || saving}
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
      <div>
        <button type="submit" disabled={!canEdit || saving || !form.recurso_id}>
          {saving ? 'Guardando...' : 'Toggle publicar'}
        </button>
      </div>
    </form>
  );
}
