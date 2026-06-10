import { useMemo } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { useSearchParams } from 'react-router-dom';

import PaginationControls from '../../components/tables/PaginationControls';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { formatNumber } from '../../utils/formatters';
import { usePagination } from '../../hooks';
import { usePermissions } from '../../hooks/usePermissions';

function AdminClassesPage() {
  const me = useAuthStore((state) => state.user);
  const [searchParams, setSearchParams] = useSearchParams();
  const paginationPage = parseInt(searchParams.get('page') || '1', 10);

  const { canAny } = usePermissions(me);
  const canView = canAny(['CLASS_VIEW', 'SYSTEM_ADMIN']);

  const paginationUrl = '/api/v1/profesor/clases/';



  const { items: rows, pagination, loading, error: apiError } = usePagination(paginationUrl, {
    skip: !canView,
    params: { page: paginationPage },
    pageMode: true,
  });

  const summaryCards = useMemo(() => {
    return [
      {
        title: 'Clases visibles',
        value: rows.length,
        subtitle: rows.length > 0 ? 'Registros de la pagina actual' : 'Sin clases cargadas',
      },
      {
        title: 'Total paginado',
        value: pagination.total,
        subtitle: 'Resultados totales en el backend',
      },
      {
        title: 'Siguiente pagina',
        value: pagination.hasNext ? 'Si' : 'No',
        subtitle: 'Indica si hay más registros',
      },
      {
        title: 'Pagina previa',
        value: pagination.hasPrevious ? 'Si' : 'No',
        subtitle: 'Indica si existe retroceso',
      },
    ];
  }, [rows.length, pagination.total, pagination.hasNext, pagination.hasPrevious]);

  function updatePage(nextPage) {
    const safePage = nextPage > 0 ? nextPage : 1;
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('page', String(safePage));
    setSearchParams(nextParams, { replace: true });
  }

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="admin-classes-title">Admin Escolar: Clases</h2>
            <p>No tienes permisos para ver clases.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="admin-classes-title">Admin Escolar: Clases</h2>
          <p>Lectura desde `GET /api/v1/profesor/clases/` con paginación.</p>
        </div>
      </header>

      {apiError ? <div className="error-box" data-testid="admin-classes-error" role="alert" aria-live="assertive">{apiError}</div> : null}

      <div className="summary-grid" data-testid="admin-classes-summary">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => (
              <SummarySkeleton key={index} />
            ))
          : summaryCards.map((item) => (
              <article key={item.title} className="summary-tile">
                <small>{item.title}</small>
                <strong>{formatNumber(item.value)}</strong>
                <span>{item.subtitle}</span>
              </article>
            ))}
      </div>

      <article className="card section-card">
        <div className="section-card-head">
          <div>
            <h3>Listado de Clases</h3>
            <p>Clases del profesor con sus datos de operación visibles para administración.</p>
          </div>
        </div>

        {loading ? (
          <TableLoadingState />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Curso</th>
                  <th>Asignatura</th>
                  <th>Profesor ID</th>
                  <th>Estudiantes</th>
                  <th>Activa</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.curso_nombre}</td>
                    <td>{row.asignatura_nombre}</td>
                    <td>{row.profesor_id ?? '-'}</td>
                    <td>{row.total_estudiantes ?? '-'}</td>
                    <td>{row.activo ? 'Si' : 'No'}</td>
                  </tr>
                ))}
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan="6">Sin registros</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <PaginationControls
        page={paginationPage}
        count={pagination.total}
        hasNext={pagination.hasNext}
        hasPrevious={pagination.hasPrevious}
        onPageChange={updatePage}
        loading={loading}
      />
    </section>
  );
}

export default AdminClassesPage;


