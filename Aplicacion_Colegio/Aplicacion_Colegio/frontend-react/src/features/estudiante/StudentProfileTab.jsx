import { SectionStatus } from './StudentSelfCommon';

export function StudentProfileTab({ profile, loading, error, statusBadges = [] }) {
  return (
    <article className="card section-card">
      <h3>Mi Perfil</h3>
      {statusBadges.length ? (
        <div className="badge-row">
          {statusBadges.map((badge) => (
            <span
              key={badge.label}
              className={`badge ${badge.tone === 'warning' ? 'badge-warning' : badge.tone === 'danger' ? 'badge-danger' : 'badge-inactive'}`}
              title={badge.description || badge.label}
            >
              {badge.label}
            </span>
          ))}
        </div>
      ) : null}
      {loading ? (
        <SectionStatus title="Cargando perfil" description="Obteniendo los datos personales del estudiante." loading />
      ) : error ? (
        <div className="error-box" role="alert" aria-live="assertive">{error}</div>
      ) : (
        <dl className="detail-list">
          <div>
            <dt>Nombre</dt>
            <dd>{profile?.nombre_completo || profile?.nombre || 'Pendiente'}</dd>
          </div>
          <div>
            <dt>Correo</dt>
            <dd>{profile?.email || profile?.correo || 'Pendiente'}</dd>
          </div>
          <div>
            <dt>RUT</dt>
            <dd>{profile?.rut || 'Pendiente'}</dd>
          </div>
          <div>
            <dt>Curso actual</dt>
            <dd>{profile?.curso_actual || profile?.curso || 'Sin asignar'}</dd>
          </div>
        </dl>
      )}
    </article>
  );
}
