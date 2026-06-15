/**
 * Shared loading skeleton components for section-level loading.
 * Used across admin, profesor, and other feature pages.
 */

export function SummarySkeleton() {
  return (
    <article className="summary-tile summary-skeleton" aria-hidden="true">
      <div className="skeleton-line skeleton-sm" />
      <div className="skeleton-line skeleton-md" />
    </article>
  );
}

export function TableLoadingState() {
  return (
    <div className="table-wrap" aria-busy="true" aria-live="polite" role="status">
      <div className="skeleton-table" />
    </div>
  );
}
