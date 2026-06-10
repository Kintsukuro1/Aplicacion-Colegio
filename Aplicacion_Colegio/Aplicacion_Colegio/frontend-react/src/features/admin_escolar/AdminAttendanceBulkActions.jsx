/**
 * Bulk action panel for attendance state updates.
 */
const ATTENDANCE_STATES = [
  { value: 'P', label: 'Presente' },
  { value: 'A', label: 'Ausente' },
  { value: 'T', label: 'Tardanza' },
  { value: 'J', label: 'Justificada' },
];

export function AdminAttendanceBulkActions({
  selectedCount,
  bulkState,
  processingBulk,
  bulkResult,
  onBulkStateChange,
  onBulkUpdate,
  onRetryFailed,
}) {
  return (
    <div className="card section-card">
      <div className="bulk-actions-bar">
        <span>{selectedCount} seleccionado(s) en la pagina actual.</span>
        <div className="bulk-actions-row">
          <select value={bulkState} onChange={(e) => onBulkStateChange(e.target.value)} disabled={processingBulk}>
            {ATTENDANCE_STATES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button type="button" onClick={onBulkUpdate} disabled={processingBulk || selectedCount === 0}>
            {processingBulk ? 'Actualizando...' : 'Actualizar Estado Seleccionados'}
          </button>
        </div>
      </div>

      {bulkResult ? (
        <p className="bulk-result-text">
          Actualizacion masiva completada: {bulkResult.success} ok, {bulkResult.failed} con error
          {bulkResult.failed > 0
            ? ` (IDs: ${bulkResult.failedIds.slice(0, 5).join(', ')}${bulkResult.failed > 5 ? ', ...' : ''})`
            : ''}
          .
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
