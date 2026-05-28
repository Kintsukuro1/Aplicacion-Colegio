import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { useSearchParams } from 'react-router-dom';

import PaginationControls from '../../components/tables/PaginationControls';
import SearchBar from '../../components/forms/SearchBar';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { formatNumber } from '../../utils/formatters';
import { usePagination } from '../../hooks';
import { usePermissionChecks } from '../../hooks/usePermissionChecks';
import { useFormCRUD } from '../../hooks/useFormCRUD';
import { useBulkDeactivate } from '../../hooks/useBulkDeactivate';

import { AdminStudentsForm } from './AdminStudentsForm';
import { AdminStudentsTable } from './AdminStudentsTable';
import { AdminStudentsBulkActions } from './AdminStudentsBulkActions';

const EMPTY_FORM = {
  email: '',
  rut: '',
  nombre: '',
  apellido_paterno: '',
  apellido_materno: '',
  is_active: true,
};
const SEARCH_DEBOUNCE_MS = 300;

export default function AdminStudentsPage() {
  const me = useAuthStore((state) => state.user);
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(searchParams.get('q') || '');
  const [search, setSearch] = useState(searchParams.get('q') || '');
  const searchDebounceRef = useRef(null);
  const [selectedIds, setSelectedIds] = useState([]);

  useEffect(() => {
    return () => {
      clearTimeout(searchDebounceRef.current);
    };
  }, []);

  const { canView, canCreate, canUpdate, canDelete } = usePermissionChecks({
    viewCapabilities: ['STUDENT_VIEW', 'SYSTEM_ADMIN'],
    createCapabilities: ['STUDENT_EDIT', 'SYSTEM_ADMIN'],
    updateCapabilities: ['STUDENT_EDIT', 'SYSTEM_ADMIN'],
    deleteCapabilities: ['STUDENT_EDIT', 'SYSTEM_ADMIN'],
  });

  const { form, setForm, editingId, startEdit, resetForm, saving, create, update, delete: deleteRecord, error: formError } = useFormCRUD({
    initialForm: EMPTY_FORM,
    endpoint: '/api/v1/estudiantes/',
    onSuccess: () => { refetch(); setSelectedIds([]); },
  });

  const { deactivate: doBulkDeactivate, saving: bulkSaving, bulkResult, retry: retryBulkDeactivate } = useBulkDeactivate({
    bulkEndpoint: '/api/v1/estudiantes/bulk-deactivate/',
    singleEndpoint: '/api/v1/estudiantes/',
    onSuccess: () => { refetch(); setSelectedIds([]); },
  });

  const { items: rows, loading, error: paginationError, pagination, goToPage, refetch } = usePagination('/api/v1/estudiantes/', {
    params: search ? { search } : {},
    skip: !me,
  });

  const summaryCards = useMemo(() => {
    const total = rows.length;
    const activeCount = rows.filter((row) => row.is_active).length;
    const inactiveCount = total - activeCount;
    return [
      { title: 'Estudiantes visibles', value: total, subtitle: total > 0 ? 'Resultados de la página actual' : 'Sin registros cargados' },
      { title: 'Activos', value: activeCount, subtitle: 'Cuentas habilitadas para usar la plataforma' },
      { title: 'Inactivos', value: inactiveCount, subtitle: 'Cuentas desactivadas en esta página' },
      { title: 'Selección', value: selectedIds.length, subtitle: 'Marcados para desactivación masiva' },
    ];
  }, [rows, selectedIds.length]);

  const canSubmit = useMemo(() => Boolean(form.email && form.rut && form.nombre && form.apellido_paterno), [form]);
  const formLocked = editingId ? !canUpdate : !canCreate;

  function updatePage(nextPage) {
    const safePage = nextPage > 0 ? nextPage : 1;
    goToPage(safePage);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('page', String(safePage));
    if (search) nextParams.set('q', search);
    else nextParams.delete('q');
    setSearchParams(nextParams, { replace: true });
  }

  function handleSearch(value) {
    setSearchInput(value);
    clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      setSearch(value);
      const nextParams = new URLSearchParams(searchParams);
      nextParams.set('page', '1');
      if (value) nextParams.set('q', value);
      else nextParams.delete('q');
      setSearchParams(nextParams, { replace: true });
    }, SEARCH_DEBOUNCE_MS);
  }

  function toggleSelect(studentId) {
    setSelectedIds((prev) => prev.includes(studentId) ? prev.filter((id) => id !== studentId) : [...prev, studentId]);
  }

  function toggleSelectAllCurrentPage() {
    const currentIds = rows.map((row) => row.id);
    setSelectedIds((currentIds.length > 0 && currentIds.every((id) => selectedIds.includes(id))) ? [] : currentIds);
  }

  function onChange(name, value) { setForm((prev) => ({ ...prev, [name]: value })); }

  async function onSubmit(event) {
    event.preventDefault();
    if (formLocked || !canSubmit) return;
    try {
      if (editingId) await update();
      else await create();
    } catch {}
  }

  async function onDelete(studentId) {
    if (!canDelete || !window.confirm('Desactivar este estudiante?')) return;
    try { await deleteRecord(studentId); } catch {}
  }

  async function onBulkDeactivate() {
    if (!canDelete || selectedIds.length === 0 || !window.confirm(`Desactivar ${selectedIds.length} estudiante(s)?`)) return;
    await doBulkDeactivate(selectedIds);
  }

  async function onRetryFailedBulkDeactivate() {
    if (!bulkResult || bulkResult.failed === 0) return;
    await retryBulkDeactivate(bulkResult.failedIds);
  }

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="admin-students-title">Admin Escolar: Estudiantes</h2>
            <p>No tienes permisos para ver estudiantes.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="admin-students-title">Admin Escolar: Estudiantes</h2>
          <p>Gestión de estudiantes con búsqueda, edición y desactivación masiva.</p>
        </div>
      </header>

      <SearchBar
        value={searchInput}
        onChange={handleSearch}
        placeholder="Buscar por nombre, email, RUT..."
        label="Buscar estudiantes"
      />

      {paginationError ? <div className="error-box" data-testid="admin-students-error" role="alert" aria-live="assertive">{paginationError}</div> : null}

      {!canCreate ? <p>Modo restringido: falta capability `STUDENT_EDIT` para crear.</p> : null}

      <div className="summary-grid" data-testid="admin-students-summary">
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

      {canCreate || canUpdate ? (
        <AdminStudentsForm
          form={form}
          editingId={editingId}
          formLocked={formLocked}
          saving={saving}
          formError={formError}
          canSubmit={canSubmit}
          onChange={onChange}
          resetForm={resetForm}
          onSubmit={onSubmit}
        />
      ) : (
        <div className="card">
          <p>Tienes permisos de lectura, pero no de edición (`STUDENT_EDIT`).</p>
        </div>
      )}

      {loading ? (
        <TableLoadingState />
      ) : (
        <AdminStudentsTable
          rows={rows}
          selectedIds={selectedIds}
          canUpdate={canUpdate}
          canDelete={canDelete}
          onToggleSelect={toggleSelect}
          onToggleSelectAll={toggleSelectAllCurrentPage}
          onStartEdit={startEdit}
          onDelete={onDelete}
        />
      )}

      {canDelete ? (
        <AdminStudentsBulkActions
          selectedCount={selectedIds.length}
          bulkSaving={bulkSaving}
          bulkResult={bulkResult}
          onBulkDeactivate={onBulkDeactivate}
          onRetryFailed={onRetryFailedBulkDeactivate}
        />
      ) : null}

      <PaginationControls
        page={pagination.currentPage}
        count={pagination.total}
        hasNext={pagination.currentPage < pagination.totalPages}
        hasPrevious={pagination.currentPage > 1}
        onPageChange={updatePage}
        loading={loading}
      />
    </section>
  );
}
