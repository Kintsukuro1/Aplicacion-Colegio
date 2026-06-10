import { useMemo, useReducer } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { useSearchParams } from 'react-router-dom';

import PaginationControls from '../../components/tables/PaginationControls';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { apiClient } from '../../services/apiClient';
import { usePagination } from '../../hooks';
import { formatNumber, normalizeGrade } from '../../utils/formatters';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';

import { AdminGradesForm } from './AdminGradesForm';
import { AdminGradesTable } from './AdminGradesTable';
import { AdminGradesBulkActions } from './AdminGradesBulkActions';

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

const EMPTY_FORM = {
  evaluacion: '',
  estudiante: '',
  nota: '',
};

function createInitialState(searchParams) {
  const initialPage = Number.parseInt(searchParams.get('page') || '1', 10);
  return {
    page: Number.isFinite(initialPage) && initialPage > 0 ? initialPage : 1,
    selectedIds: [],
    form: EMPTY_FORM,
    editingId: null,
    processingBulk: false,
    saving: false,
    bulkResult: null,
  };
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET_PAGE':
      return { ...state, page: action.page, selectedIds: [], bulkResult: null };
    case 'SET_FORM_FIELD':
      return { ...state, form: { ...state.form, [action.name]: action.value } };
    case 'START_EDIT':
      return {
        ...state,
        editingId: action.row.id_calificacion,
        form: {
          evaluacion: String(action.row.evaluacion),
          estudiante: String(action.row.estudiante),
          nota: String(normalizeGrade(action.row.nota) ?? action.row.nota ?? ''),
        },
      };
    case 'RESET_FORM':
      return { ...state, editingId: null, form: EMPTY_FORM };
    case 'TOGGLE_SELECT': {
      const id = action.id;
      const prev = state.selectedIds;
      return {
        ...state,
        selectedIds: prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
      };
    }
    case 'TOGGLE_SELECT_ALL': {
      const currentIds = action.rows.map((row) => row.id_calificacion);
      const allSelected = currentIds.length > 0 && currentIds.every((id) => state.selectedIds.includes(id));
      return { ...state, selectedIds: allSelected ? [] : currentIds };
    }
    case 'CLEAR_SELECTION':
      return { ...state, selectedIds: [] };
    case 'SET_PROCESSING_BULK':
      return { ...state, processingBulk: action.value };
    case 'SET_SAVING':
      return { ...state, saving: action.value };
    case 'SET_BULK_RESULT':
      return { ...state, bulkResult: action.value };
    default:
      return state;
  }
}

export default function AdminGradesPage() {
  const me = useAuthStore((state) => state.user);
  const [searchParams, setSearchParams] = useSearchParams();
  const [state, dispatch] = useReducer(reducer, searchParams, createInitialState);
  const toast = useToast();
  const { canAny } = usePermissions(me);

  const canView = useMemo(
    () => canAny(['GRADE_VIEW', 'GRADE_CREATE', 'GRADE_EDIT', 'GRADE_DELETE', 'SYSTEM_ADMIN']),
    [canAny]
  );
  const canCreate = useMemo(() => canAny(['GRADE_CREATE', 'SYSTEM_ADMIN']), [canAny]);
  const canEdit = useMemo(() => canAny(['GRADE_EDIT', 'SYSTEM_ADMIN']), [canAny]);
  const canDelete = useMemo(() => canAny(['GRADE_DELETE', 'SYSTEM_ADMIN']), [canAny]);
  
  const paginationUrl = '/api/v1/profesor/calificaciones/';
  const { items: rows, pagination, loading, error: apiError, refetch: refetchGrades } = usePagination(paginationUrl, {
    params: { page: state.page },
    pageMode: true,
    skip: !canView,
  });

  const formLocked = state.editingId ? !canEdit : !canCreate;
  const canSubmit = useMemo(() => {
    return Boolean(state.form.evaluacion && state.form.estudiante && state.form.nota !== '');
  }, [state.form]);

  function toPayload() {
    return {
      evaluacion: Number.parseInt(state.form.evaluacion, 10),
      estudiante: Number.parseInt(state.form.estudiante, 10),
      nota: normalizeGrade(state.form.nota) ?? Number.parseFloat(state.form.nota),
    };
  }

  function startEdit(row) {
    if (!canEdit) {
      toast.error('No tienes permisos para editar calificaciones.');
      return;
    }
    dispatch({ type: 'START_EDIT', row });
  }

  function updatePage(nextPage) {
    const safePage = nextPage > 0 ? nextPage : 1;
    dispatch({ type: 'SET_PAGE', page: safePage });
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('page', String(safePage));
    setSearchParams(nextParams, { replace: true });
  }

  const summaryCards = useMemo(() => {
    return [
      {
        title: 'Calificaciones visibles',
        value: rows.length,
        subtitle: rows.length > 0 ? 'Registros de la pagina actual' : 'Sin calificaciones cargadas',
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
  }, [pagination.total, pagination.hasNext, pagination.hasPrevious, rows.length]);

  async function onSubmit(event) {
    event.preventDefault();

    if (formLocked) {
      toast.error(state.editingId ? 'No tienes permisos para editar calificaciones.' : 'No tienes permisos para crear calificaciones.');
      return;
    }
    if (!canSubmit) {
      return;
    }

    dispatch({ type: 'SET_SAVING', value: true });
    try {
      const payload = toPayload();
      if (state.editingId) {
        await apiClient.patch(`/api/v1/profesor/calificaciones/${state.editingId}/`, payload);
      } else {
        await apiClient.post('/api/v1/profesor/calificaciones/', payload);
      }
      await refetchGrades();
      dispatch({ type: 'RESET_FORM' });
      toast.success(state.editingId ? 'Calificacion actualizada' : 'Calificacion creada');
    } catch (err) {
      toast.error(err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo guardar calificacion.');
    } finally {
      dispatch({ type: 'SET_SAVING', value: false });
    }
  }

  async function onDelete(gradeId) {
    if (!canDelete) {
      toast.error('No tienes permisos para eliminar calificaciones.');
      return;
    }

    if (!window.confirm('Eliminar esta calificacion?')) {
      return;
    }

    try {
      await apiClient.del(`/api/v1/profesor/calificaciones/${gradeId}/`);
      await refetchGrades();
      toast.success('Calificacion eliminada');
    } catch (err) {
      toast.error(err.payload?.detail || 'No se pudo eliminar calificacion.');
    }
  }

  async function runBulkDelete(targetIds) {
    dispatch({ type: 'SET_PROCESSING_BULK', value: true });
    dispatch({ type: 'SET_BULK_RESULT', value: null });

    try {
      let result;

      try {
        const payload = await apiClient.post('/api/v1/profesor/calificaciones/bulk-delete/', {
          ids: targetIds,
        });
        result = toBulkResult(payload);
      } catch (batchError) {
        if (!isBatchEndpointUnavailable(batchError)) {
          throw batchError;
        }

        const results = await Promise.all(
          targetIds.map(async (gradeId) => {
            try {
              await apiClient.del(`/api/v1/profesor/calificaciones/${gradeId}/`);
              return { ok: true, id: gradeId };
            } catch (_) {
              return { ok: false, id: gradeId };
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

      dispatch({ type: 'SET_BULK_RESULT', value: result });
      await refetchGrades();
      dispatch({ type: 'CLEAR_SELECTION' });
      toast.success('Eliminacion masiva completada');
    } catch (err) {
      toast.error(err.payload?.detail || 'No se pudo completar la eliminacion masiva.');
    } finally {
      dispatch({ type: 'SET_PROCESSING_BULK', value: false });
    }
  }

  async function onBulkDelete() {
    if (!canDelete) {
      toast.error('No tienes permisos para eliminar calificaciones.');
      return;
    }

    if (state.selectedIds.length === 0) {
      toast.error('Selecciona al menos una calificacion para eliminar.');
      return;
    }

    if (!window.confirm(`Eliminar ${state.selectedIds.length} calificacion(es) seleccionada(s)?`)) {
      return;
    }

    await runBulkDelete(state.selectedIds);
  }

  async function retryFailedBulkDelete() {
    if (!state.bulkResult || state.bulkResult.failed === 0) {
      return;
    }
    await runBulkDelete(state.bulkResult.failedIds);
  }

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="admin-grades-title">Admin Escolar: Calificaciones</h2>
            <p>No tienes permisos para ver calificaciones.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>Admin Escolar: Calificaciones</h2>
          <p>Lectura desde `/api/v1/profesor/calificaciones/`.</p>
        </div>
      </header>

      {apiError ? <div className="error-box" data-testid="admin-grades-error" role="alert" aria-live="assertive">{apiError}</div> : null}
      {!canCreate ? <p>Modo restringido: falta capability `GRADE_CREATE` para crear.</p> : null}
      {!canDelete ? <p>Modo restringido: falta capability `GRADE_DELETE` para eliminacion masiva.</p> : null}

      {canCreate || canEdit ? (
        <AdminGradesForm
          form={state.form}
          editingId={state.editingId}
          formLocked={formLocked}
          saving={state.saving}
          canSubmit={canSubmit}
          onChange={(name, value) => dispatch({ type: 'SET_FORM_FIELD', name, value })}
          onCancel={() => dispatch({ type: 'RESET_FORM' })}
          onSubmit={onSubmit}
        />
      ) : null}

      <div className="summary-grid" data-testid="admin-grades-summary">
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
            <h3>Listado de Calificaciones</h3>
            <p>Calificaciones del profesor con sus datos de operación visibles para administración.</p>
          </div>
        </div>

        {loading ? (
          <TableLoadingState />
        ) : (
          <AdminGradesTable
            rows={rows}
            selectedIds={state.selectedIds}
            canEdit={canEdit}
            canDelete={canDelete}
            processingBulk={state.processingBulk}
            onToggleSelect={(id) => dispatch({ type: 'TOGGLE_SELECT', id })}
            onToggleSelectAll={() => dispatch({ type: 'TOGGLE_SELECT_ALL', rows })}
            onStartEdit={startEdit}
            onDelete={onDelete}
          />
        )}
      </article>

      {canDelete ? (
        <AdminGradesBulkActions
          selectedCount={state.selectedIds.length}
          processingBulk={state.processingBulk}
          bulkResult={state.bulkResult}
          onBulkDelete={onBulkDelete}
          onRetryFailed={retryFailedBulkDelete}
        />
      ) : null}

      <PaginationControls
        page={state.page}
        count={pagination.total}
        hasNext={pagination.hasNext}
        hasPrevious={pagination.hasPrevious}
        onPageChange={updatePage}
        loading={loading}
      />
    </section>
  );
}
