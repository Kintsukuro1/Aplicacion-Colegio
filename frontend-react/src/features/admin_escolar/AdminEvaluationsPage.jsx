import { useRef, useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { useSearchParams } from 'react-router-dom';

import PaginationControls from '../../components/tables/PaginationControls';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { usePagination } from '../../hooks';
import { formatNumber } from '../../utils/formatters';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';
import { apiClient } from '../../services/apiClient';

function isBatchEndpointUnavailable(error) {
  return error?.status === 404 || error?.status === 405;
}

function toBulkResult(payload, fallbackFailedIds = []) {
  const failedIds = Array.isArray(payload?.failed_ids)
    ? payload.failed_ids
    : Array.isArray(payload?.failedIds)
      ? payload.failedIds
      : fallbackFailedIds;

  const success = Number.isFinite(payload?.success) ? payload.success : 0;
  const failed = Number.isFinite(payload?.failed) ? payload.failed : failedIds.length;
  return { success, failed, failedIds };
}

export default function AdminEvaluationsPage() {
  const me = useAuthStore((state) => state.user);
  const [searchParams, setSearchParams] = useSearchParams();
  const initialPage = Number.parseInt(searchParams.get('page') || '1', 10);
  const page = Number.isFinite(initialPage) && initialPage > 0 ? initialPage : 1;
  const [selectedIds, setSelectedIds] = useState([]);
  const [processingBulk, setProcessingBulk] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const lastBulkTargetActiveRef = useRef(null);
  const { canAny } = usePermissions(me);

  const canView = canAny(['GRADE_VIEW', 'GRADE_CREATE', 'GRADE_EDIT', 'GRADE_DELETE', 'SYSTEM_ADMIN']);
  const canEdit = canAny(['GRADE_EDIT', 'SYSTEM_ADMIN']);
  const toast = useToast();
  const paginationUrl = '/api/v1/evaluaciones/';
  const { items: rows, pagination, loading, error: apiError, refetch } = usePagination(paginationUrl, {
    skip: !canView,
  });



  function updatePage(nextPage) {
    const safePage = nextPage > 0 ? nextPage : 1;
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('page', String(safePage));
    setSearchParams(nextParams, { replace: true });
    setSelectedIds([]);
    setBulkResult(null);
  }

  function toggleSelect(evaluationId) {
    setSelectedIds((prev) => {
      if (prev.includes(evaluationId)) {
        return prev.filter((id) => id !== evaluationId);
      }
      return [...prev, evaluationId];
    });
  }

  function toggleSelectAllCurrentPage() {
    const currentIds = rows.map((row) => row.id_evaluacion);
    const allSelected = currentIds.length > 0 && currentIds.every((id) => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds([]);
      return;
    }
    setSelectedIds(currentIds);
  }

  async function runBulkToggleActive(targetIds, targetActive) {
    setProcessingBulk(true);
    setBulkResult(null);
    lastBulkTargetActiveRef.current = targetActive;

    try {
      let result;

      try {
        const payload = await apiClient.post('/api/v1/profesor/evaluaciones/bulk-toggle-active/', {
          ids: targetIds,
          activa: targetActive,
        });
        result = toBulkResult(payload);
      } catch (batchError) {
        if (!isBatchEndpointUnavailable(batchError)) {
          throw batchError;
        }

        const results = await Promise.all(
          targetIds.map(async (evaluationId) => {
            try {
              await apiClient.patch(`/api/v1/profesor/evaluaciones/${evaluationId}/`, { activa: targetActive });
              return { ok: true, id: evaluationId };
            } catch (_) {
              return { ok: false, id: evaluationId };
            }
          })
        );
        const failedIds = results.reduce((acc, item) => {
          if (!item.ok) {
            acc.push(item.id);
          }
          return acc;
        }, []);
        const success = results.length - failedIds.length;
        result = toBulkResult({ success, failed: failedIds.length }, failedIds);
      }

      setBulkResult(result);
      await refetch();
      setSelectedIds([]);
      toast.success('Actualizacion masiva completada');
    } catch (err) {
      toast.error(err.payload?.detail || 'No se pudo completar la actualizacion masiva.');
    } finally {
      setProcessingBulk(false);
    }
  }

  async function onBulkToggleActive(targetActive) {
    if (!canEdit) {
      toast.error('No tienes permisos para editar evaluaciones.');
      return;
    }

    if (selectedIds.length === 0) {
      toast.error('Selecciona al menos una evaluacion para actualizar.');
      return;
    }

    const label = targetActive ? 'activar' : 'desactivar';
    if (!window.confirm(`${label} ${selectedIds.length} evaluacion(es) seleccionada(s)?`)) {
      return;
    }

    await runBulkToggleActive(selectedIds, targetActive);
  }

  async function retryFailedBulkUpdate() {
    if (!bulkResult || bulkResult.failed === 0 || lastBulkTargetActiveRef.current === null) {
      return;
    }
    await runBulkToggleActive(bulkResult.failedIds, lastBulkTargetActiveRef.current);
  }

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="admin-evaluations-title">Admin Escolar: Evaluaciones</h2>
            <p>No tienes permisos para ver evaluaciones.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="admin-evaluations-title">Admin Escolar: Evaluaciones</h2>
          <p>Lectura desde `GET /api/v1/profesor/evaluaciones/`.</p>
        </div>
      </header>

      {apiError ? <div className="error-box" data-testid="admin-evaluations-error" role="alert" aria-live="assertive">{apiError}</div> : null}
      {!canEdit ? <p>Modo restringido: falta capability `GRADE_EDIT` para edicion masiva.</p> : null}

      <div className="summary-grid" data-testid="admin-evaluations-summary">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => (
              <SummarySkeleton key={index} />
            ))
          : [
              { title: 'Evaluaciones visibles', value: rows.length },
              { title: 'Total paginado', value: pagination.total },
              { title: 'Siguiente pagina', value: pagination.hasNext ? 'Si' : 'No' },
              { title: 'Pagina previa', value: pagination.hasPrevious ? 'Si' : 'No' },
            ].map((item) => (
              <article key={item.title} className="summary-tile">
                <small>{item.title}</small>
                <strong>{formatNumber(item.value)}</strong>
              </article>
            ))}
      </div>

      {loading ? (
        <TableLoadingState />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={rows.length > 0 && rows.every((row) => selectedIds.includes(row.id_evaluacion))}
                    onChange={toggleSelectAllCurrentPage}
                    disabled={!canEdit || rows.length === 0 || processingBulk}
                  />
                </th>
                <th>ID</th>
                <th>Clase</th>
                <th>Nombre</th>
                <th>Fecha</th>
                <th>Ponderacion</th>
                <th>Tipo</th>
                <th>Activa</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id_evaluacion}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(row.id_evaluacion)}
                      onChange={() => toggleSelect(row.id_evaluacion)}
                      disabled={!canEdit || processingBulk}
                    />
                  </td>
                  <td>{row.id_evaluacion}</td>
                  <td>{row.clase}</td>
                  <td>{row.nombre}</td>
                  <td>{row.fecha_evaluacion}</td>
                  <td>{row.ponderacion}</td>
                  <td>{row.tipo_evaluacion}</td>
                  <td>{row.activa ? 'Si' : 'No'}</td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td colSpan="8">Sin registros</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}

      {canEdit ? (
        <div className="card section-card">
          <div className="bulk-actions-bar">
            <span>{selectedIds.length} seleccionado(s) en la pagina actual.</span>
            <div className="bulk-actions-row">
              <button
                type="button"
                className="secondary"
                onClick={() => onBulkToggleActive(true)}
                disabled={processingBulk || selectedIds.length === 0}
              >
                {processingBulk ? 'Procesando...' : 'Activar Seleccionadas'}
              </button>
              <button
                type="button"
                className="danger"
                onClick={() => onBulkToggleActive(false)}
                disabled={processingBulk || selectedIds.length === 0}
              >
                {processingBulk ? 'Procesando...' : 'Desactivar Seleccionadas'}
              </button>
            </div>
          </div>

          {bulkResult ? (
            <p className="bulk-result-text">
              Actualizacion masiva completada: {bulkResult.success} ok, {bulkResult.failed} con error
              {bulkResult.failed > 0 ? ` (IDs: ${bulkResult.failedIds.slice(0, 5).join(', ')}${bulkResult.failed > 5 ? ', ...' : ''})` : ''}.
            </p>
          ) : null}

          {bulkResult && bulkResult.failed > 0 ? (
            <div className="bulk-retry-actions">
              <button type="button" className="secondary" onClick={retryFailedBulkUpdate} disabled={processingBulk}>
                {processingBulk ? 'Reintentando...' : 'Reintentar Fallidos'}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      <PaginationControls
        page={page}
        count={pagination.total}
        hasNext={pagination.hasNext}
        hasPrevious={pagination.hasPrevious}
        onPageChange={updatePage}
        loading={loading}
      />
    </section>
  );
}


