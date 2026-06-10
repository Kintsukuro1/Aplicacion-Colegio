import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { apiClient } from '../../services/apiClient';
import PaginationControls from '../../components/tables/PaginationControls';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { formatNumber } from '../../utils/formatters';
import { usePagination } from '../../hooks';
import { usePermissionChecks } from '../../hooks/usePermissionChecks';
import { useFormCRUD } from '../../hooks/useFormCRUD';
import { useEventFilters } from '../../hooks/useEventFilters';
import { useToast } from '../../components/feedback/Toast';
import { CalendarFilterForm } from './CalendarFilterForm';
import { CalendarEventForm } from './CalendarEventForm';
import { CalendarEventsTable } from './CalendarEventsTable';
import { CalendarGrid } from './CalendarGrid';

const EMPTY_FORM = {
  titulo: '',
  descripcion: '',
  tipo: 'actividad',
  fecha_inicio: '',
  fecha_fin: '',
  hora_inicio: '',
  hora_fin: '',
  todo_el_dia: true,
  lugar: '',
  visibilidad: 'todos',
  es_feriado_nacional: false,
  color: '#3B82F6',
};

function normalizeFormForApi(form) {
  return {
    ...form,
    fecha_fin: form.fecha_fin || null,
    hora_inicio: form.todo_el_dia ? null : form.hora_inicio || null,
    hora_fin: form.todo_el_dia ? null : form.hora_fin || null,
    descripcion: form.descripcion || '',
    lugar: form.lugar || '',
  };
}

export default function CalendarEventsPage() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialPage = Number.parseInt(searchParams.get('page') || '1', 10);
  const [initialized, setInitialized] = useState(false);
  const [appliedFilters, setAppliedFilters] = useState({});
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'

  const { canView, canCreate, canUpdate, canDelete } = usePermissionChecks({
    viewCapabilities: ['ANNOUNCEMENT_VIEW', 'SYSTEM_ADMIN'],
    createCapabilities: ['ANNOUNCEMENT_CREATE', 'SYSTEM_ADMIN'],
    updateCapabilities: ['ANNOUNCEMENT_EDIT', 'SYSTEM_ADMIN'],
    deleteCapabilities: ['ANNOUNCEMENT_DELETE', 'SYSTEM_ADMIN'],
  });

  const {
    filters,
    updateFilter,
    clearFilters,
    activeFilters,
  } = useEventFilters({
    tipo: '',
    mes: '',
    anio: '',
    desde: '',
    hasta: '',
  });

  const {
    form,
    setForm,
    editingId,
    startEdit,
    resetForm,
    saving,
    create,
    update,
    delete: deleteRecord,
  } = useFormCRUD({
    initialForm: EMPTY_FORM,
    endpoint: '/api/v1/calendario/',
    getId: (record) => record.id_evento,
    mapRecordToForm: (record) => ({
      titulo: record.titulo || '',
      descripcion: record.descripcion || '',
      tipo: record.tipo || 'actividad',
      fecha_inicio: record.fecha_inicio || '',
      fecha_fin: record.fecha_fin || '',
      hora_inicio: record.hora_inicio || '',
      hora_fin: record.hora_fin || '',
      todo_el_dia: Boolean(record.todo_el_dia),
      lugar: record.lugar || '',
      visibilidad: record.visibilidad || 'todos',
      es_feriado_nacional: Boolean(record.es_feriado_nacional),
      color: record.color || '#3B82F6',
    }),
    mapFormToPayload: normalizeFormForApi,
    onSuccess: () => {
      refetch();
    },
  });

  const {
    items: rows,
    loading,
    error: paginationError,
    pagination,
    goToPage,
    refetch,
  } = usePagination('/api/v1/calendario/', {
    pageMode: true,
    params: appliedFilters,
    skip: !canView || !initialized,
  });

  const { data: scheduleData } = useQuery({
    queryKey: ['profesor-horario', 'calendar'],
    queryFn: () => apiClient.get('/api/v1/profesor/mi-horario/'),
    retry: false, // If it fails (e.g., admin), don't retry
    enabled: canView && initialized,
  });

  const activeFiltersCount = useMemo(
    () => Object.keys(appliedFilters).length,
    [appliedFilters]
  );

  const summaryCards = useMemo(() => ([
    {
      title: 'Eventos visibles',
      value: rows.length,
      subtitle: 'Registros en la página actual',
    },
    {
      title: 'Clases Semanales',
      value: scheduleData?.total_bloques || 0,
      subtitle: scheduleData ? 'Tu horario cargado' : 'No disponible para tu rol',
    },
    {
      title: 'Filtros activos',
      value: activeFiltersCount,
      subtitle: 'Campos usados para acotar la búsqueda',
    },
    {
      title: 'Estado',
      value: loading ? 'Cargando' : 'Listo',
      subtitle: canCreate || canUpdate || canDelete ? 'Con permisos de operación' : 'Solo lectura',
    },
  ]), [activeFiltersCount, canCreate, canDelete, canUpdate, loading, rows.length, scheduleData]);

  function updatePage(nextPage) {
    const safePage = nextPage > 0 ? nextPage : 1;
    goToPage(safePage);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('page', String(safePage));
    setSearchParams(nextParams, { replace: true });
  }

  useEffect(() => {
    if (!canView) {
      return;
    }
    const safePage = Number.isFinite(initialPage) && initialPage > 0 ? initialPage : 1;
    goToPage(safePage);
    setInitialized(true);
  }, [canView, goToPage, initialPage]);

  function onChange(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function onStartEdit(row) {
    if (!canUpdate) {
      toast.error('No tienes permisos para editar eventos.');
      return;
    }
    startEdit(row);
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (editingId && !canUpdate) {
      toast.error('No tienes permisos para editar eventos.');
      return;
    }
    if (!editingId && !canCreate) {
      toast.error('No tienes permisos para crear eventos.');
      return;
    }
    if (!form.titulo || !form.fecha_inicio || !form.tipo) {
      toast.error('Completa titulo, tipo y fecha de inicio.');
      return;
    }

    try {
      if (editingId) {
        await update();
      } else {
        await create();
      }
      resetForm();
    } catch (err) {
      // Errors are handled by useFormCRUD.
    }
  }

  async function onDelete(row) {
    if (!canDelete) {
      toast.error('No tienes permisos para eliminar eventos.');
      return;
    }
    if (!window.confirm(`Eliminar evento ${row.titulo}?`)) {
      return;
    }

    try {
      await deleteRecord(row.id_evento);
    } catch (err) {
      // Errors are handled by useFormCRUD.
    }
  }

  async function onApplyFilters(event) {
    event.preventDefault();
    setAppliedFilters(activeFilters);
    updatePage(1);
  }

  function onClearFilters() {
    clearFilters();
    setAppliedFilters({});
    updatePage(1);
  }

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="calendar-events-title">Calendario Escolar</h2>
            <p>No tienes permisos para ver eventos del calendario.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="calendar-events-title">Calendario Escolar</h2>
          <p>Visualiza y administra los eventos académicos y feriados del colegio.</p>
        </div>
      </header>

      {paginationError ? <div className="error-box" data-testid="calendar-events-error" role="alert" aria-live="assertive">{paginationError}</div> : null}

      <div className="summary-grid" data-testid="calendar-events-summary">
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

      <CalendarFilterForm
        filters={filters}
        loading={loading}
        updateFilter={updateFilter}
        onApplyFilters={onApplyFilters}
        onClearFilters={onClearFilters}
      />

      {(canCreate || canUpdate) ? (
        <CalendarEventForm
          form={form}
          editingId={editingId}
          saving={saving}
          onChange={onChange}
          onSubmit={onSubmit}
          onReset={resetForm}
        />
      ) : null}

      <article className="card section-card">
        <div className="section-card-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3>Eventos</h3>
            <p>Eventos académicos y administrativos cargados para la consulta actual.</p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', backgroundColor: 'var(--color-bg-inset, #f3f4f6)', padding: '0.25rem', borderRadius: '8px' }}>
            <button 
              type="button" 
              className={viewMode === 'grid' ? 'primary' : 'secondary'} 
              onClick={() => setViewMode('grid')}
              style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: 'none' }}
            >
              Vista Calendario
            </button>
            <button 
              type="button" 
              className={viewMode === 'list' ? 'primary' : 'secondary'} 
              onClick={() => setViewMode('list')}
              style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: 'none' }}
            >
              Vista Lista
            </button>
          </div>
        </div>

        {loading ? (
          <TableLoadingState />
        ) : viewMode === 'grid' ? (
          <div style={{ marginTop: '1.5rem' }}>
            <CalendarGrid 
              events={rows}
              schedule={scheduleData?.horario}
              canEdit={canUpdate || canDelete}
              onEdit={onStartEdit}
              currentMonth={appliedFilters.mes}
              currentYear={appliedFilters.anio}
            />
          </div>
        ) : (
          <CalendarEventsTable
            events={rows}
            canEdit={canUpdate || canDelete}
            savingId={null}
            onEdit={onStartEdit}
            onDelete={onDelete}
          />
        )}
      </article>

      {viewMode === 'list' && (
        <PaginationControls
          page={pagination.currentPage}
          count={pagination.total}
          hasPrevious={pagination.currentPage > 1}
          hasNext={pagination.currentPage < pagination.totalPages}
          onPageChange={updatePage}
          loading={loading}
        />
      )}
    </section>
  );
}


