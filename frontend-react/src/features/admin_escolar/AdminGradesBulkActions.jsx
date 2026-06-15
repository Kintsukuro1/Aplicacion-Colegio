/**
 * Panel for executing bulk actions (deletion) on selected grades.
 */
export function AdminGradesBulkActions({
  selectedCount,
  processingBulk,
  bulkResult,
  onBulkDelete,
  onRetryFailed,
}) {
  return (
    <div className="card section-card">
      <div className="bulk-actions-bar">
        <span>{selectedCount} seleccionado(s) en la pagina actual.</span>
        <button
          type="button"
          className="danger"
          onClick={onBulkDelete}
          disabled={processingBulk || selectedCount === 0}
        >
          {processingBulk ? 'Eliminando...' : 'Eliminar Seleccionadas'}
        </button>
      </div>

      {bulkResult ? (
        <p className="bulk-result-text">
          Eliminacion masiva completada: {bulkResult.success} ok, {bulkResult.failed} con error
          {bulkResult.failed > 0 ? ` (IDs: ${bulkResult.failedIds.slice(0, 5).join(', ')}${bulkResult.failed > 5 ? ', ...' : ''})` : ''}.
        </p>
      ) : null}

      {bulkResult && bulkResult.failed > 0 ? (
        <div className="bulk-retry-actions">
          <button type="button" className="secondary" onClick={onRetryFailed} disabled={processingBulk}>
            {processingBulk ? 'Reintentando...' : 'Reintentar Fallidos'}
          </button>
        </div>
      ) : null}
    </div>
  );
}
