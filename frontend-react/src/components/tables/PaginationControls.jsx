export default function PaginationControls({
  page,
  count,
  pageSize = 50,
  hasPrevious,
  hasNext,
  onPageChange,
  loading,
}) {
  const totalPages = Math.max(1, Math.ceil((count || 0) / pageSize));

  return (
    <div className="card section-card">
      <div className="bulk-actions-bar">
        <button
          type="button"
          className="secondary"
          disabled={loading || !hasPrevious || page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Anterior
        </button>
        <span>
          Pagina {page} de {totalPages} (Total: {count || 0})
        </span>
        <button
          type="button"
          className="secondary"
          disabled={loading || !hasNext || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
