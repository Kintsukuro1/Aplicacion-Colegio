/**
 * Filter controls for attendance page — class and date selectors.
 */
export function AdminAttendanceFilters({ classes, selectedClass, selectedDate, onChangeClass, onChangeDate }) {
  return (
    <div className="card form-grid">
      <h3>Filtros</h3>

      <label>
        Clase
        <select value={selectedClass} onChange={(e) => onChangeClass(e.target.value)}>
          <option value="">Seleccionar</option>
          {classes.map((row) => (
            <option key={row.id} value={row.id}>
              {row.curso_nombre} - {row.asignatura_nombre}
            </option>
          ))}
        </select>
      </label>

      <label>
        Fecha
        <input type="date" value={selectedDate} onChange={(e) => onChangeDate(e.target.value)} />
      </label>
    </div>
  );
}
