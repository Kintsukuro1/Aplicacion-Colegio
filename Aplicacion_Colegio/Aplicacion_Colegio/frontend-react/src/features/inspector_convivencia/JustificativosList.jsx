import { TableLoadingState } from '../../components/feedback/TableLoadingState';

/**
 * List of pending justifications with quick action buttons.
 */
export function JustificativosList({ justifications, loading, saving, canReview, onQuickReview, onSelectForReview }) {
  return (
    <article className="card section-card">
      <h3>Justificativos pendientes ({justifications.length})</h3>
      {loading ? (
        <TableLoadingState />
      ) : justifications.length === 0 ? (
        <p>Sin justificativos pendientes.</p>
      ) : (
        <ul>
          {justifications.slice(0, 15).map((item) => (
            <li key={item.id}>
              <strong>#{item.id}</strong> {item.estudiante} - {item.fecha_ausencia}
              <div>
                <button
                  type="button"
                  disabled={!canReview || saving}
                  onClick={() => onQuickReview(item.id, 'APROBADO')}
                >
                  Aprobar
                </button>
                <button
                  type="button"
                  disabled={!canReview || saving}
                  onClick={() => onQuickReview(item.id, 'RECHAZADO')}
                >
                  Rechazar
                </button>
                <button
                  type="button"
                  onClick={() => onSelectForReview(String(item.id))}
                  disabled={!canReview || saving}
                >
                  Usar en formulario
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
