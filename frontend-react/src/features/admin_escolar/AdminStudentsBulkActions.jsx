/**
 * Panel for bulk actions (deactivation) on selected students.
 */
export function AdminStudentsBulkActions({ selectedCount, bulkSaving, bulkResult, onBulkDeactivate, onRetryFailed }) {
  return (
    <div className="card section-card">
      <div className="bulk-actions-bar">
        <span>{selectedCount} seleccionado(s) en la pagina actual.</span>
        <button
          type="button"
          className="danger"
          onClick={onBulkDeactivate}
          disabled={bulkSaving || selectedCount === 0}
        >
          {bulkSaving ? 'Procesando...' : 'Desactivar Seleccionados'}
        </button>
      </div>

      {bulkResult ? (
        <p className="bulk-result-text" role="status" aria-live="polite">
          Desactivacion masiva completada: {bulkResult.successCount} ok, {bulkResult.failCount} con error
          {bulkResult.failCount > 0 ? ` (IDs: ${bulkResult.details.filter((r) => !r.success).slice(0, 5).map((r) => r.id).join(', ')}${bulkResult.failCount > 5 ? ', ...' : ''})` : ''}.
        </p>
      ) : null}

      {bulkResult && bulkResult.failCount > 0 ? (
        <div className="bulk-retry-actions">
          <button type="button" className="secondary" onClick={onRetryFailed} disabled={bulkSaving}>
            {bulkSaving ? 'Reintentando...' : 'Reintentar Fallidos'}
          </button>
        </div>
      ) : null}
    </div>
  );
}
