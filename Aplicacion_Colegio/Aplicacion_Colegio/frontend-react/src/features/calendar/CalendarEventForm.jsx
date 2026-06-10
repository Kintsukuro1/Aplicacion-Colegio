import { EVENT_TYPES, VISIBILITY } from './CalendarFilterForm';

export function CalendarEventForm({ form, editingId, saving, onChange, onSubmit, onReset }) {
  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3 className="full">{editingId ? `Editar #${editingId}` : 'Nuevo Evento'}</h3>
      <label>
        Titulo
        <input value={form.titulo} onChange={(e) => onChange('titulo', e.target.value)} required disabled={saving} />
      </label>
      <label>
        Tipo
        <select value={form.tipo} onChange={(e) => onChange('tipo', e.target.value)} disabled={saving}>
          {EVENT_TYPES.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
      </label>
      <label>
        Visibilidad
        <select value={form.visibilidad} onChange={(e) => onChange('visibilidad', e.target.value)} disabled={saving}>
          {VISIBILITY.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
      </label>
      <label>
        Fecha Inicio
        <input type="date" value={form.fecha_inicio} onChange={(e) => onChange('fecha_inicio', e.target.value)} required disabled={saving} />
      </label>
      <label>
        Fecha Fin
        <input type="date" value={form.fecha_fin} onChange={(e) => onChange('fecha_fin', e.target.value)} disabled={saving} />
      </label>
      <label>
        Hora Inicio
        <input type="time" value={form.hora_inicio} onChange={(e) => onChange('hora_inicio', e.target.value)} disabled={saving || form.todo_el_dia} />
      </label>
      <label>
        Hora Fin
        <input type="time" value={form.hora_fin} onChange={(e) => onChange('hora_fin', e.target.value)} disabled={saving || form.todo_el_dia} />
      </label>
      <label>
        Lugar
        <input value={form.lugar} onChange={(e) => onChange('lugar', e.target.value)} disabled={saving} />
      </label>
      <label>
        Color
        <input type="color" value={form.color} onChange={(e) => onChange('color', e.target.value)} disabled={saving} />
      </label>
      <label>
        Todo el dia
        <input type="checkbox" checked={form.todo_el_dia} onChange={(e) => onChange('todo_el_dia', e.target.checked)} disabled={saving} />
      </label>
      <label>
        Feriado nacional
        <input
          type="checkbox"
          checked={form.es_feriado_nacional}
          onChange={(e) => onChange('es_feriado_nacional', e.target.checked)}
          disabled={saving}
        />
      </label>
      <label className="full">
        Descripcion
        <input value={form.descripcion} onChange={(e) => onChange('descripcion', e.target.value)} disabled={saving} />
      </label>

      <div className="actions full">
        <button type="submit" disabled={saving}>{editingId ? 'Guardar Cambios' : 'Crear Evento'}</button>
        <button type="button" className="secondary" onClick={onReset} disabled={saving}>Cancelar</button>
      </div>
    </form>
  );
}
