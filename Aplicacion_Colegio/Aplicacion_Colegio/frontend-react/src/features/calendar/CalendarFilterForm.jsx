export const EVENT_TYPES = [
  'feriado',
  'vacaciones',
  'evaluacion',
  'reunion',
  'actividad',
  'ceremonia',
  'administrativo',
  'otro',
];

export const VISIBILITY = ['todos', 'profesores', 'estudiantes', 'apoderados', 'administrativos'];

export function CalendarFilterForm({ filters, loading, updateFilter, onApplyFilters, onClearFilters }) {
  return (
    <form className="card form-grid" onSubmit={onApplyFilters}>
      <h3 className="full">Filtros</h3>
      <label>
        Tipo
        <select value={filters.tipo} onChange={(e) => updateFilter('tipo', e.target.value)}>
          <option value="">Todos</option>
          {EVENT_TYPES.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
      </label>
      <label>
        Mes
        <input
          type="number"
          min="1"
          max="12"
          value={filters.mes}
          onChange={(e) => updateFilter('mes', e.target.value)}
        />
      </label>
      <label>
        Anio
        <input
          type="number"
          min="2020"
          max="2100"
          value={filters.anio}
          onChange={(e) => updateFilter('anio', e.target.value)}
        />
      </label>
      <label>
        Desde
        <input type="date" value={filters.desde} onChange={(e) => updateFilter('desde', e.target.value)} />
      </label>
      <label>
        Hasta
        <input type="date" value={filters.hasta} onChange={(e) => updateFilter('hasta', e.target.value)} />
      </label>
      <div className="actions full">
        <button type="submit" className="secondary" disabled={loading}>Aplicar Filtros</button>
        <button
          type="button"
          onClick={onClearFilters}
          disabled={loading}
        >
          Limpiar
        </button>
      </div>
    </form>
  );
}
