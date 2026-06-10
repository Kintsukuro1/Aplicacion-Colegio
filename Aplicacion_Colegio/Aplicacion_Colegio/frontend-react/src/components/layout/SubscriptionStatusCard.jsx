import { Link } from 'react-router-dom';

function getUsagePercent(current, limit) {
  if (!limit || limit <= 0 || limit >= 999999) {
    return null;
  }
  return Math.min(100, Math.round((current / limit) * 100));
}

export default function SubscriptionStatusCard({
  planName,
  daysRemaining,
  studentsUsed = 0,
  studentsLimit,
  messagesUsed = 0,
  messagesLimit,
}) {
  const studentsPercent = getUsagePercent(studentsUsed, studentsLimit);
  const messagesPercent = getUsagePercent(messagesUsed, messagesLimit);

  return (
    <article className="card section-card subscription-status-card">
      <div className="section-card-head">
        <div>
          <h3>Suscripción Actual</h3>
          <p>{planName || 'Sin plan asignado'}</p>
        </div>
        {daysRemaining !== null && daysRemaining !== undefined ? (
          <span className="badge badge-active">{daysRemaining} días</span>
        ) : (
          <span className="badge badge-inactive">Ilimitado</span>
        )}
      </div>

      <div className="subscription-status-grid">
        <div>
          <span className="subscription-status-label">Estudiantes</span>
          <strong>{studentsUsed}</strong>
          {studentsPercent !== null ? <div className="usage-bar"><span style={{ width: `${studentsPercent}%` }} /></div> : null}
        </div>
        <div>
          <span className="subscription-status-label">Mensajes</span>
          <strong>{messagesUsed}</strong>
          {messagesPercent !== null ? <div className="usage-bar"><span style={{ width: `${messagesPercent}%` }} /></div> : null}
        </div>
      </div>

      <div className="subscription-status-actions">
        <Link className="quick-action-link" to="/planes">Ver planes</Link>
        <Link className="quick-action-link" to="/pagos/historial">Historial</Link>
      </div>
    </article>
  );
}
