const TIPOS_IMPORTACION = ['estudiantes', 'profesores', 'apoderados'];

/**
 * Section for handling CSV template downloads and bulk data imports.
 */
export function ImportSection({ tipo, importing, exporting, importResult, onTipoChange, onFileChange, onDownloadTemplate, onImportSubmit }) {
  return (
    <>
      <article className="card section-card">
        <h3>Plantillas CSV</h3>
        <label>
          Tipo
          <select value={tipo} onChange={(e) => onTipoChange(e.target.value)} disabled={exporting || importing}>
            {TIPOS_IMPORTACION.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <div className="actions section-card">
          <button type="button" onClick={onDownloadTemplate} disabled={exporting || importing}>
            Descargar Plantilla
          </button>
        </div>
      </article>

      <article className="card section-card">
        <h3>Importacion Masiva</h3>
        <form className="form-grid" onSubmit={onImportSubmit}>
          <label>
            Tipo de Carga
            <select value={tipo} onChange={(e) => onTipoChange(e.target.value)} disabled={importing || exporting}>
              {TIPOS_IMPORTACION.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <label>
            Archivo (CSV/XLSX)
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={onFileChange}
              disabled={importing || exporting}
            />
          </label>

          <div className="actions full">
            <button type="submit" disabled={importing || exporting}>
              {importing ? 'Importando...' : 'Importar Datos'}
            </button>
          </div>
        </form>

        {importResult ? (
          <div className="import-summary">
            <p>
              Resultado: {importResult.exitosos} exitosos, {importResult.fallidos} fallidos,
              total procesados {importResult.total_procesados}.
            </p>
            {Array.isArray(importResult.errores) && importResult.errores.length > 0 ? (
              <details>
                <summary>Ver errores ({importResult.errores.length})</summary>
                <ul>
                  {importResult.errores.map((errorItem) => (
                    <li key={errorItem}>{errorItem}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </div>
        ) : null}
      </article>
    </>
  );
}
