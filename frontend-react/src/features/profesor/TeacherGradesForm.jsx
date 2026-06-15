export function TeacherGradesForm({ form, evaluations, students, canCreate, isPending, onChange, onSubmit, canSubmit }) {
  if (!canCreate) {
    return null;
  }

  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <h3>Nueva Calificacion</h3>

      <label>
        Evaluacion
        <select value={form.evaluacion} onChange={(e) => onChange('evaluacion', e.target.value)} required disabled={isPending}>
          <option value="">Seleccionar</option>
          {evaluations.map((row) => (
            <option key={row.id_evaluacion} value={row.id_evaluacion}>
              {row.nombre} ({row.fecha_evaluacion})
            </option>
          ))}
        </select>
      </label>

      <label>
        Estudiante
        <select value={form.estudiante} onChange={(e) => onChange('estudiante', e.target.value)} required disabled={isPending}>
          <option value="">Seleccionar</option>
          {students.map((row) => (
            <option key={row.id} value={row.id}>
              {row.nombre} {row.apellido_paterno}
            </option>
          ))}
        </select>
      </label>

      <label>
        Nota
        <input value={form.nota} onChange={(e) => onChange('nota', e.target.value)} required disabled={isPending} />
      </label>

      <div className="actions full">
        <button type="submit" disabled={!canSubmit || isPending}>
          {isPending ? 'Creando...' : 'Crear'}
        </button>
      </div>
    </form>
  );
}
