import { useEffect, useMemo, useReducer, useRef } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { useSearchParams } from 'react-router-dom';

import PaginationControls from '../../components/tables/PaginationControls';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { apiClient } from '../../services/apiClient';
import { useFetch, usePagination } from '../../hooks';
import { formatNumber } from '../../utils/formatters';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';

import { AdminAttendanceFilters } from './AdminAttendanceFilters';
import { AdminAttendanceForm } from './AdminAttendanceForm';
import { AdminAttendanceTable } from './AdminAttendanceTable';
import { AdminAttendanceBulkActions } from './AdminAttendanceBulkActions';

import {
  ATTENDANCE_STATES,
  isBatchEndpointUnavailable,
  toBulkResult,
  createInitialState,
  adminAttendanceReducer
} from './adminAttendanceReducer';

export default function AdminAttendancePage() {
  const me = useAuthStore((state) => state.user);
  const [searchParams, setSearchParams] = useSearchParams();
  const [state, dispatch] = useReducer(adminAttendanceReducer, searchParams, createInitialState);
  const lastBulkStateRef = useRef(null);
  const toast = useToast();
  const { canAny } = usePermissions(me);

  const canView = useMemo(
    () => canAny(['CLASS_VIEW_ATTENDANCE', 'CLASS_TAKE_ATTENDANCE', 'SYSTEM_ADMIN']),
    [canAny]
  );
  const canEdit = useMemo(() => canAny(['CLASS_TAKE_ATTENDANCE', 'SYSTEM_ADMIN']), [canAny]);
  const canSubmit = useMemo(() => {
    return Boolean(state.form.clase && state.form.estudiante && state.form.fecha && state.form.estado);
  }, [state.form]);

  function updateFilters(nextClass, nextDate, nextPage = 1) {
    dispatch({ type: 'SET_FILTERS', selectedClass: nextClass, selectedDate: nextDate, page: nextPage });
    const nextParams = new URLSearchParams(searchParams);
    if (nextClass) nextParams.set('clase_id', nextClass); else nextParams.delete('clase_id');
    if (nextDate) nextParams.set('fecha', nextDate); else nextParams.delete('fecha');
    nextParams.set('page', String(nextPage > 0 ? nextPage : 1));
    setSearchParams(nextParams, { replace: true });
  }

  function updatePage(nextPage) {
    const safePage = nextPage > 0 ? nextPage : 1;
    dispatch({ type: 'SET_PAGE', page: safePage });
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('page', String(safePage));
    setSearchParams(nextParams, { replace: true });
  }

  function onChange(name, value) { dispatch({ type: 'SET_FORM_FIELD', name, value }); }
  function resetForm() { dispatch({ type: 'RESET_FORM' }); }

  function startEdit(row) {
    if (!canEdit) { toast.error('No tienes permisos.'); return; }
    dispatch({ type: 'START_EDIT', row });
  }

  function toPayload() {
    return {
      clase: Number.parseInt(state.form.clase, 10),
      estudiante: Number.parseInt(state.form.estudiante, 10),
      fecha: state.form.fecha,
      estado: state.form.estado,
      tipo_asistencia: state.form.tipo_asistencia || null,
      observaciones: state.form.observaciones || null,
    };
  }

  // --- Data fetching ---

  const { data: classesResp, loading: classesLoading, error: classesError } = useFetch('/api/v1/profesor/clases/', { skip: !canView });
  useEffect(() => {
    const classRows = Array.isArray(classesResp?.results) ? classesResp.results : [];
    dispatch({ type: 'SET_CLASSES', classes: classRows });
    if (!state.selectedClass && classRows.length) {
      updateFilters(String(classRows[0].id), state.selectedDate);
    }
  }, [classesResp, classesError]);

  const paginationUrl = '/api/v1/profesor/asistencias/';
  const paginationParams = { page: state.page };
  if (state.selectedClass) paginationParams.clase_id = state.selectedClass;
  if (state.selectedDate) paginationParams.fecha = state.selectedDate;

  const { items: attendanceRows, pagination, loading: attendanceLoading, error: attendanceError, refetch: refetchAttendance } = usePagination(paginationUrl, {
    params: paginationParams,
    pageMode: true,
    skip: !canView || !state.selectedClass,
  });

  const totalPages = Math.max(1, pagination.totalPages);
  const hasNext = state.page < totalPages;
  const hasPrevious = state.page > 1;

  useEffect(() => {
    if (Array.isArray(attendanceRows)) {
      dispatch({ type: 'SET_ROWS', rows: attendanceRows });
    }
  }, [attendanceRows, attendanceError]);

  async function runBulkUpdateState(targetIds, targetState) {
    dispatch({ type: 'SET_PROCESSING_BULK', value: true });
    dispatch({ type: 'SET_BULK_RESULT', value: null });
    lastBulkStateRef.current = targetState;
    try {
      let result;
      try {
        const payload = await apiClient.post('/api/v1/profesor/asistencias/bulk-update-state/', { ids: targetIds, estado: targetState });
        result = toBulkResult(payload);
      } catch (batchError) {
        if (!isBatchEndpointUnavailable(batchError)) throw batchError;
        const results = await Promise.all(targetIds.map(async (attendanceId) => {
          try { await apiClient.patch(`/api/v1/profesor/asistencias/${attendanceId}/`, { estado: targetState }); return { ok: true, id: attendanceId }; } catch (_) { return { ok: false, id: attendanceId }; }
        }));
        const failedIds = results.reduce((acc, item) => { if (!item.ok) acc.push(item.id); return acc; }, []);
        result = toBulkResult({ success: results.length - failedIds.length, failed: failedIds.length }, failedIds);
      }
      dispatch({ type: 'SET_BULK_RESULT', value: result });
      await refetchAttendance?.();
      toast.success('Actualizacion masiva completada');
    } catch (err) { toast.error(err.payload?.detail || 'No se pudo completar la actualizacion masiva.'); }
    finally { dispatch({ type: 'SET_PROCESSING_BULK', value: false }); }
  }

  async function onBulkUpdateState() {
    if (!canEdit) { toast.error('No tienes permisos.'); return; }
    if (state.selectedIds.length === 0) { toast.error('Selecciona al menos una.'); return; }
    const targetLabel = ATTENDANCE_STATES.find((option) => option.value === state.bulkState)?.label || state.bulkState;
    if (!window.confirm(`Actualizar ${state.selectedIds.length} a ${targetLabel}?`)) return;
    await runBulkUpdateState(state.selectedIds, state.bulkState);
  }

  async function retryFailedBulkUpdate() {
    if (!state.bulkResult || state.bulkResult.failed === 0 || !lastBulkStateRef.current) return;
    await runBulkUpdateState(state.bulkResult.failedIds, lastBulkStateRef.current);
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (!canEdit) { toast.error('No tienes permisos.'); return; }
    if (!canSubmit) return;
    dispatch({ type: 'SET_SAVING', value: true });
    try {
      const payload = toPayload();
      if (state.editingId) await apiClient.patch(`/api/v1/profesor/asistencias/${state.editingId}/`, payload);
      else await apiClient.post('/api/v1/profesor/asistencias/', payload);
      await refetchAttendance?.();
      resetForm();
      toast.success(state.editingId ? 'Asistencia actualizada' : 'Asistencia creada');
    } catch (err) { toast.error(err.payload?.detail || 'Error al guardar.'); }
    finally { dispatch({ type: 'SET_SAVING', value: false }); }
  }

  async function onDelete(attendanceId) {
    if (!canEdit) { toast.error('No tienes permisos.'); return; }
    if (!window.confirm('Eliminar esta asistencia?')) return;
    try {
      await apiClient.del(`/api/v1/profesor/asistencias/${attendanceId}/`);
      await refetchAttendance?.();
      toast.success('Asistencia eliminada');
    } catch (err) { toast.error(err.payload?.detail || 'Error al eliminar.'); }
  }

  const loading = !!(classesLoading || attendanceLoading);

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="admin-attendance-title">Admin Escolar: Asistencias</h2>
            <p>No tienes permisos para ver asistencias.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="admin-attendance-title">Admin Escolar: Asistencias</h2>
          <p>CRUD de asistencias sobre API v1 (`/api/v1/profesor/asistencias/`).</p>
        </div>
      </header>

      {classesError || attendanceError ? <div className="error-box" data-testid="admin-attendance-error" role="alert" aria-live="assertive">{classesError || attendanceError}</div> : null}
      {!canEdit ? <p>Modo restringido: falta capability `CLASS_TAKE_ATTENDANCE` para edicion masiva.</p> : null}

      <AdminAttendanceFilters
        classes={state.classes}
        selectedClass={state.selectedClass}
        selectedDate={state.selectedDate}
        onChangeClass={(value) => updateFilters(value, state.selectedDate)}
        onChangeDate={(value) => updateFilters(state.selectedClass, value, 1)}
      />

      {canEdit ? (
        <AdminAttendanceForm
          classes={state.classes}
          form={state.form}
          editingId={state.editingId}
          saving={state.saving}
          canSubmit={canSubmit}
          onChange={onChange}
          onSubmit={onSubmit}
          onCancel={resetForm}
        />
      ) : null}

      <div className="summary-grid" data-testid="admin-attendance-summary">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => (
              <SummarySkeleton key={index} />
            ))
          : [
              { title: 'Registros visibles', value: state.rows.length },
              { title: 'Total paginado', value: pagination.total },
              { title: 'Siguiente pagina', value: hasNext ? 'Si' : 'No' },
              { title: 'Pagina previa', value: hasPrevious ? 'Si' : 'No' },
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
        <AdminAttendanceTable
          rows={state.rows}
          selectedIds={state.selectedIds}
          canEdit={canEdit}
          processingBulk={state.processingBulk}
          onToggleSelect={(id) => dispatch({ type: 'TOGGLE_SELECT', id })}
          onToggleSelectAll={() => dispatch({ type: 'TOGGLE_SELECT_ALL' })}
          onStartEdit={startEdit}
          onDelete={onDelete}
        />
      )}

      {canEdit ? (
        <AdminAttendanceBulkActions
          selectedCount={state.selectedIds.length}
          bulkState={state.bulkState}
          processingBulk={state.processingBulk}
          bulkResult={state.bulkResult}
          onBulkStateChange={(value) => dispatch({ type: 'SET_BULK_STATE', value })}
          onBulkUpdate={onBulkUpdateState}
          onRetryFailed={retryFailedBulkUpdate}
        />
      ) : null}

      <PaginationControls
        page={state.page}
        count={pagination.total}
        hasNext={hasNext}
        hasPrevious={hasPrevious}
        onPageChange={updatePage}
        loading={loading}
      />
    </section>
  );
}
