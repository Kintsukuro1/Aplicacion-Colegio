import { useMemo, useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import PaginationControls from '../../components/tables/PaginationControls';
import { apiClient } from '../../services/apiClient';
import { usePagination } from '../../hooks';
import { formatNumber } from '../../utils/formatters';
import FormOverlay from '../../components/forms/FormOverlay';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';

import { AdminCoursesForm } from './AdminCoursesForm';
import { AdminCoursesTable } from './AdminCoursesTable';

const EMPTY_FORM = {
  nombre: '',
  activo: true,
  nivel_id: '',
  ciclo_academico_id: '',
};

export default function AdminCoursesPage() {
  const me = useAuthStore((state) => state.user);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialPage = Number.parseInt(searchParams.get('page') || '1', 10);
  const [page, setPage] = useState(Number.isFinite(initialPage) && initialPage > 0 ? initialPage : 1);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const { canAny } = usePermissions(me);

  const canView = useMemo(() => canAny(['COURSE_VIEW', 'SYSTEM_ADMIN']), [canAny]);
  const canCreate = useMemo(() => canAny(['COURSE_CREATE', 'SYSTEM_ADMIN']), [canAny]);
  const canUpdate = useMemo(() => canAny(['COURSE_EDIT', 'SYSTEM_ADMIN']), [canAny]);
  const canDelete = useMemo(() => canAny(['COURSE_DELETE', 'SYSTEM_ADMIN']), [canAny]);
  const formLocked = editingId ? !canUpdate : !canCreate;
  const canSubmit = useMemo(() => {
    return Boolean(form.nombre && form.nivel_id);
  }, [form]);

  function updatePage(nextPage) {
    const safePage = nextPage > 0 ? nextPage : 1;
    setPage(safePage);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('page', String(safePage));
    setSearchParams(nextParams, { replace: true });
  }

  function onChange(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function startCreate() {
    if (!canCreate) {
      toast.error('No tienes permisos para crear cursos.');
      return;
    }
    setEditingId(null);
    setForm(EMPTY_FORM);
    setIsFormOpen(true);
  }

  function startEdit(row) {
    if (!canUpdate) {
      toast.error('No tienes permisos para editar cursos.');
      return;
    }
    setEditingId(row.id_curso);
    setForm({
      nombre: row.nombre || '',
      activo: Boolean(row.activo),
      nivel_id: row.nivel_id ? String(row.nivel_id) : '',
      ciclo_academico_id: row.ciclo_academico_id ? String(row.ciclo_academico_id) : '',
    });
    setIsFormOpen(true);
  }

  function handleCloseModal() {
    setIsFormOpen(false);
  }

  function toPayload() {
    const payload = {
      nombre: form.nombre,
      activo: Boolean(form.activo),
      nivel_id: Number.parseInt(form.nivel_id, 10),
    };

    if (form.ciclo_academico_id) {
      payload.ciclo_academico_id = Number.parseInt(form.ciclo_academico_id, 10);
    }
    return payload;
  }

  const paginationUrl = '/api/v1/cursos/';
  const { items: rows, pagination, loading, error: apiError } = usePagination(paginationUrl, {
    params: { page },
    pageMode: true,
    skip: !canView,
  });

  const hasNext = pagination.currentPage < pagination.totalPages;
  const hasPrevious = pagination.currentPage > 1;

  // Derive error inline (no useEffect sync needed)
  const error = apiError || '';

  const createMutation = useMutation({
    mutationFn: async (payload) => {
      return await apiClient.post('/api/v1/cursos/', payload);
    },
    onSuccess: () => {
      // Invalidate both exact page query and general list
      queryClient.invalidateQueries({ queryKey: [paginationUrl] });
      setIsFormOpen(false);
      toast.success('Curso creado exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo crear curso.');
    }
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }) => {
      return await apiClient.patch(`/api/v1/cursos/${id}/`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [paginationUrl] });
      setIsFormOpen(false);
      toast.success('Curso actualizado exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo actualizar curso.');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      return await apiClient.del(`/api/v1/cursos/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [paginationUrl] });
      toast.success('Curso eliminado exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || 'No se pudo eliminar curso.');
    }
  });

  async function onSubmit(event) {
    event.preventDefault();

    if (formLocked) {
      toast.error(editingId ? 'No tienes permisos para editar cursos.' : 'No tienes permisos para crear cursos.');
      return;
    }
    if (!canSubmit) {
      return;
    }

    const payload = toPayload();

    if (editingId) {
      await updateMutation.mutateAsync({ id: editingId, payload });
    } else {
      await createMutation.mutateAsync(payload);
    }
  }

  async function onDelete(courseId) {
    if (!canDelete) {
      toast.error('No tienes permisos para eliminar cursos.');
      return;
    }

    if (!window.confirm('¿Eliminar este curso?')) {
      return;
    }

    await deleteMutation.mutateAsync(courseId);
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="admin-courses-title">Admin Escolar: Cursos</h2>
            <p>No tienes permisos para ver cursos.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2>Admin Escolar: Cursos</h2>
          <p>CRUD de cursos utilizando FormOverlay y React Query.</p>
        </div>
        {canCreate ? (
          <button type="button" className="primary" onClick={startCreate}>
            + Nuevo Curso
          </button>
        ) : null}
      </header>

      {error && !isFormOpen ? <div className="error-box" data-testid="admin-courses-error" role="alert" aria-live="assertive">{error}</div> : null}
      {!canCreate && !canUpdate && !canDelete ? <p>Modo restringido: Solo lectura.</p> : null}

      <div className="summary-grid" data-testid="admin-courses-summary">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => (
              <SummarySkeleton key={index} />
            ))
          : (
              [
                { title: 'Cursos visibles', value: rows.length, subtitle: rows.length > 0 ? 'Registros de la pagina actual' : 'Sin cursos cargados' },
                { title: 'Total paginado', value: pagination.total, subtitle: 'Resultados totales en el backend' },
                { title: 'Siguiente pagina', value: hasNext ? 'Si' : 'No', subtitle: 'Indica si hay más registros' },
                { title: 'Pagina previa', value: hasPrevious ? 'Si' : 'No', subtitle: 'Indica si existe retroceso' },
              ]
            ).map((item) => (
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
            <h3>Listado de Cursos</h3>
            <p>Cursos con sus datos de operación visibles para administración.</p>
          </div>
        </div>

        {loading ? (
          <TableLoadingState />
        ) : (
          <AdminCoursesTable
            rows={rows}
            canUpdate={canUpdate}
            canDelete={canDelete}
            onStartEdit={startEdit}
            onDelete={onDelete}
            deletePending={deleteMutation.isPending}
          />
        )}
      </article>

      <PaginationControls
        page={page}
        count={pagination.total}
        hasNext={hasNext}
        hasPrevious={hasPrevious}
        onPageChange={updatePage}
        loading={loading}
      />

      <FormOverlay
        isOpen={isFormOpen}
        onClose={handleCloseModal}
        title={editingId ? `Editar curso #${editingId}` : 'Nuevo Curso'}
      >
        <AdminCoursesForm
          form={form}
          editingId={editingId}
          formLocked={formLocked}
          isSaving={isSaving}
          canSubmit={canSubmit}
          onChange={onChange}
          onSubmit={onSubmit}
          onClose={handleCloseModal}
        />
      </FormOverlay>
    </section>
  );
}
