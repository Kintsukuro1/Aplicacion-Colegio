export function SectionStatus({ title, description, loading = false }) {
  return (
    <div
      className="card section-card"
      aria-busy={loading ? 'true' : 'false'}
      aria-live="polite"
      role={loading ? 'status' : undefined}
      style={{ background: 'rgba(148, 163, 184, 0.06)' }}
    >
      <strong>{title}</strong>
      <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>{description}</p>
      {loading ? <div style={{ marginTop: '1rem', height: '12px', width: '60%', borderRadius: '999px', background: 'rgba(148, 163, 184, 0.14)' }} /> : null}
    </div>
  );
}

export function EmptySection({ title, description }) {
  return (
    <div className="card section-card" style={{ background: 'rgba(148, 163, 184, 0.04)' }}>
      <strong>{title}</strong>
      <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>{description}</p>
    </div>
  );
}
