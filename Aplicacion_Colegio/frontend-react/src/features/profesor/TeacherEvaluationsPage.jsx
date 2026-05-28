import { useEffect, useMemo, useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '../../services/apiClient';
import { formatNumber } from '../../utils/formatters';
import { asResults } from '../../utils/httpHelpers';
import FormOverlay from '../../components/forms/FormOverlay';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';

import { TeacherEvaluationsForm } from './TeacherEvaluationsForm';
import { TeacherEvaluationsTable } from './TeacherEvaluationsTable';

const EMPTY_FORM = {
  clase: '',
  nombre: '',
  fecha_evaluacion: '',
  ponderacion: '100.00',
  tipo_evaluacion: 'sumativa',
  periodo: '',
};

export default function TeacherEvaluationsPage() {
  const me = useAuthStore((state) => state.user);
  const { can } = usePermissions(me);
  const queryClient = useQueryClient();
  const [selectedClass, setSelectedClass] = useState('');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const toast = useToast();

  const canCreate = can('GRADE_CREATE');
  const canEdit = can('GRADE_EDIT');
  const canDelete = can('GRADE_DELETE');
  const formLocked = editingId ? !canEdit : !canCreate;

  // React Query: Clases
  const { data: classesResp, isLoading: loadingClasses, error: classesError } = useQuery({
    queryKey: ['profesor-clases'],
    queryFn: () => apiClient.get('/api/v1/profesor/clases/'),
  });
  const classes = asResults(classesResp) || [];

  // Initialize selectedClass with first class when classes load
  useEffect(() => {
    if (!selectedClass && classes.length > 0) {
      setSelectedClass(String(classes[0].id));
    }
  }, [classes, selectedClass]);

  // React Query: Evaluaciones (depende de selectedClass)
  const { data: evaluationsResp, isLoading: loadingEvaluations, error: evaluationsError } = useQuery({
    queryKey: ['profesor-evaluaciones', selectedClass],
    queryFn: () => apiClient.get(`/api/v1/profesor/evaluaciones/?clase_id=${selectedClass}`),
    enabled: !!selectedClass,
  });
  const rows = asResults(evaluationsResp) || [];

  const loading = loadingClasses || loadingEvaluations;
  const apiError = classesError || evaluationsError;

  const summary = useMemo(() => {
    const totalEvaluations = rows.length;
    const classCount = classes.length;
    const editableCount = canEdit ? totalEvaluations : 0;
    const deletableCount = canDelete ? totalEvaluations : 0;

    return [
      {
        title: 'Evaluaciones',
        value: totalEvaluations,
        subtitle: totalEvaluations > 0 ? 'Registradas en esta clase' : 'Sin evaluaciones',
      },
      {
        title: 'Clases',
        value: classCount,
        subtitle: classCount > 0 ? 'Cursos asignados' : 'No hay clases',
      },
      {
        title: 'Editables',
        value: editableCount,
        subtitle: canEdit ? 'Permiso de edición' : 'Lectura',
      },
      {
        title: 'Eliminables',
        value: deletableCount,
        subtitle: canDelete ? 'Permiso de eliminación' : 'Lectura',
      },
    ];
  }, [canDelete, canEdit, classes.length, rows.length]);

  const canSubmit = useMemo(() => {
    const canSaveCurrentAction = editingId ? canEdit : canCreate;
    return canSaveCurrentAction && Boolean(form.clase && form.nombre && form.fecha_evaluacion);
  }, [canCreate, canEdit, editingId, form]);

  function onChange(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function startCreate() {
    if (!canCreate) {
      toast.error('No tienes permisos para crear evaluaciones.');
      return;
    }
    setEditingId(null);
    setForm({
      ...EMPTY_FORM,
      clase: selectedClass || (classes[0] ? String(classes[0].id) : ''),
    });
    setIsFormOpen(true);
  }

  function startEdit(row) {
    if (!canEdit) {
      toast.error('No tienes permisos para editar evaluaciones.');
      return;
    }
    setEditingId(row.id_evaluacion);
    setForm({
      clase: String(row.clase),
      nombre: row.nombre,
      fecha_evaluacion: row.fecha_evaluacion,
      ponderacion: String(row.ponderacion),
      tipo_evaluacion: row.tipo_evaluacion,
      periodo: row.periodo || '',
    });
    setIsFormOpen(true);
  }

  function handleCloseModal() {
    setIsFormOpen(false);
  }

  const createMutation = useMutation({
    mutationFn: async (payload) => {
      return await apiClient.post('/api/v1/profesor/evaluaciones/', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesor-evaluaciones', selectedClass] });
      setIsFormOpen(false);
      toast.success('Evaluación creada exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo crear evaluación.');
    }
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }) => {
      return await apiClient.patch(`/api/v1/profesor/evaluaciones/${id}/`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesor-evaluaciones', selectedClass] });
      setIsFormOpen(false);
      toast.success('Evaluación actualizada exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo actualizar evaluación.');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      return await apiClient.del(`/api/v1/profesor/evaluaciones/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesor-evaluaciones', selectedClass] });
      toast.success('Evaluación eliminada exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || 'No se pudo eliminar evaluación.');
    }
  });

  async function onSubmit(event) {
    event.preventDefault();
    if (formLocked) {
      toast.error(editingId ? 'No tienes permisos para editar evaluaciones.' : 'No tienes permisos para crear evaluaciones.');
      return;
    }
    if (!canSubmit) {
      return;
    }

    const payload = {
      clase: Number(form.clase),
      nombre: form.nombre,
      fecha_evaluacion: form.fecha_evaluacion,
      ponderacion: form.ponderacion,
      tipo_evaluacion: form.tipo_evaluacion,
      periodo: form.periodo || null,
    };

    if (editingId) {
      await updateMutation.mutateAsync({ id: editingId, payload });
    } else {
      await createMutation.mutateAsync(payload);
    }
  }

  async function onDelete(id) {
    if (!canDelete) {
      toast.error('No tienes permisos para eliminar evaluaciones.');
      return;
    }
    if (!window.confirm('¿Eliminar esta evaluación?')) {
      return;
    }
    await deleteMutation.mutateAsync(id);
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <section>
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 data-testid="teacher-evaluations-title">Profesor: Evaluaciones</h2>
          <p>Gestión de evaluaciones mediante modales superpuestos y caché avanzado.</p>
        </div>
        {canCreate ? (
          <button type="button" className="primary" onClick={startCreate}>
            + Nueva Evaluación
          </button>
        ) : null}
      </header>

      {apiError ? <div className="error-box" data-testid="teacher-evaluations-error" role="alert" aria-live="assertive">{apiError?.message || 'Error en la petición'}</div> : null}
      {!canCreate && !canEdit && !canDelete ? <p>Modo lectura.</p> : null}

      <div className="summary-grid" data-testid="teacher-evaluations-summary">
        {loadingClasses
          ? Array.from({ length: 4 }).map((_, index) => (
              <SummarySkeleton key={index} />
            ))
          : summary.map((item) => (
              <article key={item.title} className="summary-tile">
                <small>{item.title}</small>
                <strong>{formatNumber(item.value)}</strong>
                <span>{item.subtitle}</span>
              </article>
            ))}
      </div>

      <div className="card form-grid">
        <h3>Filtro</h3>
        <label>
          Clase
          <select value={selectedClass} onChange={(e) => setSelectedClass(e.target.value)}>
            <option value="">Seleccionar</option>
            {classes.map((row) => (
              <option key={row.id} value={row.id}>
                {row.curso_nombre} - {row.asignatura_nombre}
              </option>
            ))}
          </select>
        </label>
      </div>

      <article className="card section-card">
        <div className="section-card-head">
          <div>
            <h3>Listado de Evaluaciones</h3>
            <p>Selecciona una evaluación para editar o eliminar según tus permisos.</p>
          </div>
        </div>

        {loading ? (
          <TableLoadingState />
        ) : (
          <TeacherEvaluationsTable
            rows={rows}
            canEdit={canEdit}
            canDelete={canDelete}
            isDeleting={deleteMutation.isPending}
            onStartEdit={startEdit}
            onDelete={onDelete}
          />
        )}

        {!loading && rows.length === 0 ? <p className="section-muted">No hay evaluaciones para la clase seleccionada.</p> : null}
      </article>

      <FormOverlay
        isOpen={isFormOpen}
        onClose={handleCloseModal}
        title={editingId ? `Editar Evaluación #${editingId}` : 'Nueva Evaluación'}
      >
        <TeacherEvaluationsForm
          form={form}
          classes={classes}
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
