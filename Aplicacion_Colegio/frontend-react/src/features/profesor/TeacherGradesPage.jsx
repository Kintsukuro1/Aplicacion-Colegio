import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuthStore } from '../../lib/store/useAuthStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '../../lib/apiClient';
import { formatNumber, formatGrade, normalizeGrade } from '../../lib/formatters';
import { asResults } from '../../lib/httpHelpers';
import { SummarySkeleton } from '../../components/feedback/TableLoadingState';
import { usePermissions } from '../../lib/hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';
import { TeacherGradesForm } from './TeacherGradesForm';
import { TeacherGradesTable } from './TeacherGradesTable';

const EMPTY_FORM = {
  evaluacion: '',
  estudiante: '',
  nota: '',
};

export default function TeacherGradesPage() {
  const me = useAuthStore((state) => state.user);
  const { can } = usePermissions(me);
  const queryClient = useQueryClient();
  const [selectedClass, setSelectedClass] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const toast = useToast();

  const canCreate = can('GRADE_CREATE');
  const canEdit = can('GRADE_EDIT');
  const canDelete = can('GRADE_DELETE');

  // React Query: Clases
  const { data: classesResp, isLoading: loadingClasses, error: classesError } = useQuery({
    queryKey: ['profesor-clases'],
    queryFn: () => apiClient.get('/api/v1/profesor/clases/'),
  });
  const classes = asResults(classesResp) || [];

  // Initialize selectedClass when classes load (moved to useEffect to avoid setState during render)
  useEffect(() => {
    if (!selectedClass && classes.length > 0) {
      setSelectedClass(String(classes[0].id));
    }
  }, [classes, selectedClass]);

  // React Query: Estudiantes
  const { data: studentsResp, isLoading: loadingStudents, error: studentsError } = useQuery({
    queryKey: ['estudiantes'],
    queryFn: () => apiClient.get('/api/v1/estudiantes/'),
  });
  const students = asResults(studentsResp) || [];

  // React Query: Evaluaciones (depende de selectedClass)
  const { data: evaluationsResp, isLoading: loadingEvaluations, error: evaluationsError } = useQuery({
    queryKey: ['profesor-evaluaciones', selectedClass],
    queryFn: () => apiClient.get(`/api/v1/profesor/evaluaciones/?clase_id=${selectedClass}`),
    enabled: !!selectedClass,
  });
  const evaluations = asResults(evaluationsResp) || [];

  // Auto-initialize form.evaluacion when evaluations change (moved to useEffect)
  useEffect(() => {
    if (evaluations.length > 0) {
      const currentEvalExists = evaluations.some((e) => String(e.id_evaluacion) === form.evaluacion);
      if (!currentEvalExists) {
        setForm((prev) => ({ ...prev, evaluacion: String(evaluations[0].id_evaluacion) }));
      }
    }
  }, [evaluations, form.evaluacion]);

  // React Query: Calificaciones (depende de form.evaluacion)
  const { data: gradesResp, isLoading: loadingGrades, error: gradesError } = useQuery({
    queryKey: ['profesor-calificaciones', form.evaluacion],
    queryFn: () => apiClient.get(`/api/v1/profesor/calificaciones/?evaluacion_id=${form.evaluacion}`),
    enabled: !!form.evaluacion,
  });
  const rows = asResults(gradesResp) || [];

  const loading = loadingClasses || loadingStudents || loadingEvaluations || loadingGrades;
  const apiError = classesError || studentsError || evaluationsError || gradesError;

  const summary = useMemo(() => {
    const totalGrades = rows.length;
    const totalEvaluations = evaluations.length;
    const totalStudents = students.length;
    const averageGrade = totalGrades
      ? rows.reduce((sum, row) => sum + (normalizeGrade(row.nota) ?? 0), 0) / totalGrades
      : null;

    return [
      {
        title: 'Calificaciones',
        value: totalGrades,
        subtitle: totalGrades > 0 ? 'Registros cargados' : 'Sin calificaciones todavía',
      },
      {
        title: 'Evaluaciones',
        value: totalEvaluations,
        subtitle: totalEvaluations > 0 ? 'Disponibles para la clase' : 'No hay evaluaciones',
      },
      {
        title: 'Estudiantes',
        value: totalStudents,
        subtitle: totalStudents > 0 ? 'Listado base para notas' : 'No hay estudiantes',
      },
      {
        title: 'Promedio',
        value: averageGrade,
        subtitle: totalGrades > 0 ? 'Promedio actual de la lista' : 'Sin promedio',
      },
    ];
  }, [evaluations.length, rows, students.length]);

  const canSubmit = useMemo(() => {
    return canCreate && Boolean(form.evaluacion && form.estudiante && form.nota);
  }, [canCreate, form]);

  function onChange(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function resetForm() {
    setForm((prev) => ({
      ...EMPTY_FORM,
      evaluacion: prev.evaluacion || (evaluations[0] ? String(evaluations[0].id_evaluacion) : ''),
    }));
  }

  const createMutation = useMutation({
    mutationFn: (payload) => apiClient.post('/api/v1/profesor/calificaciones/', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesor-calificaciones', form.evaluacion] });
      resetForm();
      toast.success('Calificacion creada exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo crear calificacion.');
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => apiClient.patch(`/api/v1/profesor/calificaciones/${id}/`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesor-calificaciones', form.evaluacion] });
      toast.success('Calificacion actualizada exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo actualizar calificacion.');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => apiClient.del(`/api/v1/profesor/calificaciones/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesor-calificaciones', form.evaluacion] });
      toast.success('Calificacion eliminada exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || 'No se pudo eliminar calificacion.');
    }
  });

  async function onSubmit(event) {
    event.preventDefault();
    if (!canCreate) {
      toast.error('No tienes permisos para crear calificaciones.');
      return;
    }
    if (!canSubmit) return;

    await createMutation.mutateAsync({
      evaluacion: Number(form.evaluacion),
      estudiante: Number(form.estudiante),
      nota: normalizeGrade(form.nota) ?? form.nota,
    });
  }

  async function onDelete(id) {
    if (!canDelete) {
      toast.error('No tienes permisos para eliminar calificaciones.');
      return;
    }
    if (!window.confirm('Eliminar esta calificacion?')) return;
    await deleteMutation.mutateAsync(id);
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>Profesor: Calificaciones</h2>
          <p>Registro de calificaciones con filtro por clase, evaluación e interactividad inline.</p>
        </div>
      </header>

      {apiError ? <div className="error-box" role="alert" aria-live="assertive">{apiError?.message || 'Error al cargar datos.'}</div> : null}
      {!canCreate ? <p>Modo restringido: falta capability `GRADE_CREATE` para crear.</p> : null}

      <div className="summary-grid">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => (
              <SummarySkeleton key={index} />
            ))
          : summary.map((item) => (
              <article key={item.title} className="summary-tile">
                <small>{item.title}</small>
                <strong>{item.title === 'Promedio' ? formatGrade(item.value, '-') : formatNumber(item.value)}</strong>
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

      <TeacherGradesForm
        form={form}
        evaluations={evaluations}
        students={students}
        canCreate={canCreate}
        isPending={createMutation.isPending}
        onChange={onChange}
        onSubmit={onSubmit}
        canSubmit={canSubmit}
      />

      <article className="card section-card">
        <div className="section-card-head">
          <div>
            <h3>Listado de Calificaciones</h3>
            <p>Selecciona Editar en una fila para modificar la nota directamente.</p>
          </div>
        </div>

        <TeacherGradesTable
          rows={rows}
          loading={loadingGrades}
          canEdit={canEdit}
          canDelete={canDelete}
          onUpdate={async (id, data) => {
            await updateMutation.mutateAsync({ id, payload: { nota: normalizeGrade(data.nota) ?? data.nota } });
          }}
          onDelete={onDelete}
        />
      </article>
    </section>
  );
}


