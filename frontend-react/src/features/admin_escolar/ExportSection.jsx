/**
 * Section for handling bulk data exports.
 */
export function ExportSection({
  clases,
  claseId,
  mes,
  anio,
  importing,
  exporting,
  onClaseIdChange,
  onMesChange,
  onAnioChange,
  onExport,
  onExportReporteAcademico,
  onExportAsistencia,
}) {
  return (
    <article className="card section-card">
      <h3>Exportacion de Reportes</h3>
      <div className="form-grid">
        <label>
          Clase ID
          <input
            type="number"
            min="1"
            value={claseId}
            onChange={(e) => onClaseIdChange(e.target.value)}
            placeholder="Ej: 12"
            disabled={exporting || importing}
          />
        </label>

        <label>
          Clases Disponibles (opcional)
          <select
            value={claseId}
            onChange={(e) => onClaseIdChange(e.target.value)}
            disabled={exporting || importing || clases.length === 0}
          >
            <option value="">Selecciona una clase</option>
            {clases.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id} - {item.curso_nombre} / {item.asignatura_nombre}
              </option>
            ))}
          </select>
        </label>

        <label>
          Mes (asistencia)
          <input
            type="number"
            min="1"
            max="12"
            value={mes}
            onChange={(e) => onMesChange(e.target.value)}
            placeholder="1-12"
            disabled={exporting || importing}
          />
        </label>

        <label>
          Anio (asistencia)
          <input
            type="number"
            min="2000"
            value={anio}
            onChange={(e) => onAnioChange(e.target.value)}
            placeholder="Ej: 2026"
            disabled={exporting || importing}
          />
        </label>

        <div className="actions full">
          <button type="button" onClick={() => onExport('estudiantes', '', 'estudiantes.csv')} disabled={exporting || importing}>
            Exportar Estudiantes
          </button>
          <button type="button" onClick={() => onExport('profesores', '', 'profesores.csv')} disabled={exporting || importing}>
            Exportar Profesores
          </button>
          <button type="button" onClick={onExportReporteAcademico} disabled={exporting || importing}>
            Exportar Reporte Academico
          </button>
          <button type="button" onClick={onExportAsistencia} disabled={exporting || importing}>
            Exportar Asistencia
          </button>
        </div>
      </div>
    </article>
  );
}
