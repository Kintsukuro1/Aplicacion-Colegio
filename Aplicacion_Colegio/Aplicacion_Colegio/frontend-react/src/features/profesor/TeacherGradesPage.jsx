import { useEffect, useMemo, useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '../../services/apiClient';
import { formatNumber, formatGrade, formatShortDate, normalizeGrade } from '../../utils/formatters';
import { asResults } from '../../utils/httpHelpers';
import { SummarySkeleton } from '../../components/feedback/TableLoadingState';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';
import { TeacherGradesForm } from './TeacherGradesForm';
import { TeacherGradesTable } from './TeacherGradesTable';

const EMPTY_FORM = {
  evaluacion: '',
  estudiante: '',
  nota: '',
};
const ALL_EVALUATIONS = 'all';

function toApiPath(nextUrl) {
  if (!nextUrl) {
    return '';
  }

  if (/^https?:\/\//i.test(nextUrl)) {
    const url = new URL(nextUrl);
    return `${url.pathname}${url.search}`;
  }

  return nextUrl;
}

async function fetchAllResults(path) {
  const results = [];
  let nextPath = path;

  while (nextPath) {
    const payload = await apiClient.get(nextPath);
    results.push(...asResults(payload));
    nextPath = toApiPath(payload?.next);
  }

  return results;
}

export default function TeacherGradesPage() {
  const me = useAuthStore((state) => state.user);
  const { can } = usePermissions(me);
  const queryClient = useQueryClient();
  const [selectedClass, setSelectedClass] = useState('');
  const [selectedEvaluation, setSelectedEvaluation] = useState(ALL_EVALUATIONS);
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
  const showingAllEvaluations = selectedEvaluation === ALL_EVALUATIONS;

  // Auto-initialize form.evaluacion when evaluations change (moved to useEffect)
  useEffect(() => {
    if (evaluations.length > 0) {
      const currentEvalExists = evaluations.some((e) => String(e.id_evaluacion) === form.evaluacion);
      if (!currentEvalExists) {
        setForm((prev) => ({ ...prev, evaluacion: String(evaluations[0].id_evaluacion) }));
      }
    }
  }, [evaluations, form.evaluacion]);

  useEffect(() => {
    if (selectedEvaluation !== ALL_EVALUATIONS) {
      const currentEvalExists = evaluations.some((e) => String(e.id_evaluacion) === selectedEvaluation);
      if (!currentEvalExists) {
        setSelectedEvaluation(ALL_EVALUATIONS);
      }
    }
  }, [evaluations, selectedEvaluation]);

  const gradesEndpoint = showingAllEvaluations
    ? `/api/v1/profesor/calificaciones/?clase_id=${selectedClass}`
    : `/api/v1/profesor/calificaciones/?evaluacion_id=${selectedEvaluation}`;
  const evaluationIds = evaluations.map((row) => row.id_evaluacion).join('|');
  // React Query: Calificaciones (depende del filtro de evaluacion)
  const { data: gradesResp, isLoading: loadingGrades, error: gradesError } = useQuery({
    queryKey: ['profesor-calificaciones', selectedClass, selectedEvaluation, evaluationIds],
    queryFn: async () => {
      if (showingAllEvaluations) {
        const paths = evaluations.map((row) => `/api/v1/profesor/calificaciones/?evaluacion_id=${row.id_evaluacion}`);
        const nestedResults = await Promise.all(paths.map((path) => fetchAllResults(path)));
        return { results: nestedResults.flat() };
      }

      return { results: await fetchAllResults(gradesEndpoint) };
    },
    enabled: !!selectedClass && (!showingAllEvaluations || !loadingEvaluations),
  });
  const rows = asResults(gradesResp) || [];
  const displayRows = useMemo(() => {
    return [...rows].sort((a, b) => {
      const dateCompare = String(b.fecha_creacion || '').localeCompare(String(a.fecha_creacion || ''));
      if (dateCompare !== 0) {
        return dateCompare;
      }

      return Number(b.id_calificacion || 0) - Number(a.id_calificacion || 0);
    });
  }, [rows]);
  const evaluationCounts = useMemo(() => {
    const counts = new Map();
    rows.forEach((row) => {
      const key = String(row.evaluacion || '');
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    return counts;
  }, [rows]);

  const loading = loadingClasses || loadingStudents || loadingEvaluations || loadingGrades;
  const apiError = classesError || studentsError || evaluationsError || gradesError;

  const summary = useMemo(() => {
    const totalGrades = displayRows.length;
    const totalEvaluations = evaluations.length;
    const totalStudents = students.length;
    const averageGrade = totalGrades
      ? displayRows.reduce((sum, row) => sum + (normalizeGrade(row.nota) ?? 0), 0) / totalGrades
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
  }, [displayRows, evaluations.length, students.length]);

  const canSubmit = useMemo(() => {
    return canCreate && Boolean(form.evaluacion && form.estudiante && form.nota);
  }, [canCreate, form]);

  function onChange(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function onClassChange(value) {
    setSelectedClass(value);
    setSelectedEvaluation(ALL_EVALUATIONS);
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
      queryClient.invalidateQueries({ queryKey: ['profesor-calificaciones'] });
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
      queryClient.invalidateQueries({ queryKey: ['profesor-calificaciones'] });
      toast.success('Calificacion actualizada exitosamente');
    },
    onError: (err) => {
      toast.error(err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo actualizar calificacion.');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => apiClient.del(`/api/v1/profesor/calificaciones/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profesor-calificaciones'] });
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
          <h2 data-testid="teacher-grades-title">Profesor: Calificaciones</h2>
          <p>Registro de calificaciones con filtro por clase, evaluación e interactividad inline.</p>
        </div>
      </header>

      {apiError ? <div className="error-box" data-testid="teacher-grades-error" role="alert" aria-live="assertive">{apiError?.message || 'Error al cargar datos.'}</div> : null}
      {!canCreate ? <p>Modo restringido: falta capability `GRADE_CREATE` para crear.</p> : null}

      <div className="summary-grid" data-testid="teacher-grades-summary">
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
          <select value={selectedClass} onChange={(e) => onClassChange(e.target.value)}>
            <option value="">Seleccionar</option>
            {classes.map((row) => (
              <option key={row.id} value={row.id}>
                {row.curso_nombre} - {row.asignatura_nombre}
              </option>
            ))}
          </select>
        </label>
        <div className="full evaluation-filter-group" aria-label="Filtro por evaluacion">
          <span>Evaluacion</span>
          <div className="evaluation-filter-buttons">
            <button
              type="button"
              className={selectedEvaluation === ALL_EVALUATIONS ? 'active' : ''}
              onClick={() => setSelectedEvaluation(ALL_EVALUATIONS)}
              disabled={!selectedClass}
              aria-pressed={selectedEvaluation === ALL_EVALUATIONS}
            >
              Todas
            </button>
            {evaluations.map((row) => {
              const evaluationId = String(row.id_evaluacion);
              const isActive = selectedEvaluation === evaluationId;
              const count = evaluationCounts.get(evaluationId);

              return (
                <button
                  key={row.id_evaluacion}
                  type="button"
                  className={isActive ? 'active' : ''}
                  onClick={() => setSelectedEvaluation(evaluationId)}
                  disabled={!selectedClass}
                  aria-pressed={isActive}
                >
                  {row.nombre} ({formatShortDate(row.fecha_evaluacion)}){showingAllEvaluations && count !== undefined ? ` - ${count}` : ''}
                </button>
              );
            })}
          </div>
        </div>
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
            <p>
              {showingAllEvaluations
                ? 'Vista agrupada por estudiante con todas las evaluaciones de la clase.'
                : 'Selecciona Editar en una fila para modificar la nota directamente.'}
            </p>
          </div>
        </div>

        <TeacherGradesTable
          rows={displayRows}
          evaluations={evaluations}
          loading={loadingGrades}
          canEdit={canEdit}
          canDelete={canDelete}
          showAllEvaluations={showingAllEvaluations}
          onUpdate={async (id, data) => {
            await updateMutation.mutateAsync({ id, payload: { nota: normalizeGrade(data.nota) ?? data.nota } });
          }}
          onDelete={onDelete}
        />
      </article>
    </section>
  );
}


