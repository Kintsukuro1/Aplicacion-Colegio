import { useMemo, useReducer } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';

import { apiClient } from '../../services/apiClient';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { SummarySkeleton } from '../../components/feedback/TableLoadingState';
import { formatNumber } from '../../utils/formatters';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';

import { AnotacionForm } from './AnotacionForm';
import { ReviewForm } from './ReviewForm';
import { JustificativosList } from './JustificativosList';
import { DelayForm } from './DelayForm';

const EMPTY_FORM = {
  estudiante_id: '',
  tipo: 'NEUTRA',
  categoria: 'OTRO',
  descripcion: '',
  gravedad: 1,
};

const EMPTY_REVIEW_FORM = {
  justificativo_id: '',
  estado: 'APROBADO',
  observaciones: '',
};

const EMPTY_DELAY_FORM = {
  estudiante_id: '',
  clase_id: '',
  fecha: '',
  observaciones: '',
};

function resolveError(err, fallback) {
  return err?.payload?.error || err?.payload?.detail || fallback;
}

const initialState = {
  form: EMPTY_FORM,
  reviewForm: EMPTY_REVIEW_FORM,
  delayForm: EMPTY_DELAY_FORM,
  saving: false,
  reviewSaving: false,
  delaySaving: false,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_FORM_FIELD':
      return { ...state, form: { ...state.form, [action.name]: action.value } };
    case 'SET_REVIEW_FORM_FIELD':
      return { ...state, reviewForm: { ...state.reviewForm, [action.name]: action.value } };
    case 'SET_DELAY_FORM_FIELD':
      return { ...state, delayForm: { ...state.delayForm, [action.name]: action.value } };
    case 'RESET_FORM':
      return { ...state, form: EMPTY_FORM };
    case 'RESET_REVIEW_FORM':
      return { ...state, reviewForm: EMPTY_REVIEW_FORM };
    case 'RESET_DELAY_FORM':
      return { ...state, delayForm: EMPTY_DELAY_FORM };
    case 'SET_SAVING':
      return { ...state, [action.field]: action.value };
    default:
      return state;
  }
}

export default function InspectorConvivenciaPage() {
  const me = useAuthStore((state) => state.user);
  const { canAny, isSystemAdmin } = usePermissions(me);
  const [state, dispatch] = useReducer(reducer, initialState);
  const toast = useToast();
  const queryClient = useQueryClient();

  const canCreate = isSystemAdmin || canAny(['DISCIPLINE_CREATE']);
  const canReview = isSystemAdmin || canAny(['JUSTIFICATION_APPROVE']);

  const { data: studentsData, isLoading: loadingStudents, error: errorStudentsObj } = useQuery({
    queryKey: ['inspector-estudiantes'],
    queryFn: () => apiClient.get('/api/inspector/estudiantes/')
  });
  const { data: classesData, isLoading: loadingClasses } = useQuery({
    queryKey: ['inspector-clases'],
    queryFn: () => apiClient.get('/api/v1/profesor/clases/')
  });
  const { data: justificationsData, isLoading: loadingJustifications } = useQuery({
    queryKey: ['inspector-justificativos'],
    queryFn: () => apiClient.get('/api/inspector/justificativos/')
  });

  const loading = loadingStudents || loadingClasses || loadingJustifications;
  const error = errorStudentsObj?.message;

  const students = Array.isArray(studentsData?.estudiantes) ? studentsData.estudiantes : [];
  const classes = (() => {
    if (!classesData) return [];
    return Array.isArray(classesData?.results) ? classesData.results : Array.isArray(classesData) ? classesData : [];
  })();
  const justifications = Array.isArray(justificationsData?.justificativos) ? justificationsData.justificativos : [];

  const summaryCards = useMemo(
    () => [
      {
        title: 'Estudiantes cargados',
        value: students.length,
        subtitle: students.length > 0 ? 'Disponibles para anotaciones' : 'Sin estudiantes cargados',
      },
      {
        title: 'Clases disponibles',
        value: classes.length,
        subtitle: classes.length > 0 ? 'Usables para registrar atrasos' : 'Sin clases para seleccionar',
      },
      {
        title: 'Justificativos pendientes',
        value: justifications.length,
        subtitle: justifications.length > 0 ? 'Requieren revisión' : 'Sin pendientes por revisar',
      },
    ],
    [classes.length, justifications.length, students.length]
  );

  async function onSubmit(event) {
    event.preventDefault();
    if (!canCreate) {
      toast.error('No tienes permisos para registrar anotaciones.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'saving', value: true });
    try {
      const payload = await apiClient.post('/api/inspector/anotaciones/crear/', {
        estudiante_id: Number(state.form.estudiante_id),
        tipo: state.form.tipo,
        categoria: state.form.categoria,
        descripcion: state.form.descripcion,
        gravedad: Number(state.form.gravedad),
      });
      toast.success(payload?.message || 'Anotacion registrada.');
      dispatch({ type: 'RESET_FORM' });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo registrar la anotacion.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'saving', value: false });
    }
  }

  async function onReviewSubmit(event) {
    event.preventDefault();
    if (!canReview) {
      toast.error('No tienes permisos para revisar justificativos.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'reviewSaving', value: true });
    try {
      const payload = await apiClient.post(
        `/api/inspector/justificativos/${state.reviewForm.justificativo_id}/estado/`,
        {
          estado: state.reviewForm.estado,
          observaciones: state.reviewForm.observaciones,
        }
      );
      toast.success(payload?.message || 'Justificativo actualizado.');
      dispatch({ type: 'RESET_REVIEW_FORM' });
      await queryClient.invalidateQueries({ queryKey: ['inspector-justificativos'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo actualizar el justificativo.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'reviewSaving', value: false });
    }
  }

  async function onQuickReview(justificativoId, estado) {
    if (!canReview) {
      toast.error('No tienes permisos para revisar justificativos.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'reviewSaving', value: true });
    try {
      const payload = await apiClient.post(`/api/inspector/justificativos/${justificativoId}/estado/`, {
        estado,
        observaciones: '',
      });
      toast.success(payload?.message || 'Justificativo actualizado.');
      await queryClient.invalidateQueries({ queryKey: ['inspector-justificativos'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo actualizar el justificativo.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'reviewSaving', value: false });
    }
  }

  async function onDelaySubmit(event) {
    event.preventDefault();
    if (!canCreate) {
      toast.error('No tienes permisos para registrar atrasos.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'delaySaving', value: true });
    try {
      const payload = await apiClient.post('/api/inspector/asistencia/registrar_atraso/', {
        estudiante_id: Number(state.delayForm.estudiante_id),
        clase_id: Number(state.delayForm.clase_id),
        fecha: state.delayForm.fecha,
        observaciones: state.delayForm.observaciones,
      });
      toast.success(payload?.message || 'Atraso registrado.');
      dispatch({ type: 'RESET_DELAY_FORM' });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo registrar el atraso.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'delaySaving', value: false });
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="inspector-convivencia-title">Inspector Convivencia</h2>
          <p>Registro rapido de anotaciones sobre estudiantes.</p>
        </div>
      </header>

      {error ? <div className="error-box" data-testid="inspector-convivencia-error" role="alert" aria-live="assertive">{error}</div> : null}

      <div className="summary-grid" data-testid="inspector-convivencia-summary">
        {loading
          ? Array.from({ length: 3 }).map((_, index) => (
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

      <div className="grid-2">
        <AnotacionForm
          students={students}
          form={state.form}
          saving={state.saving}
          canCreate={canCreate}
          onChange={(name, value) => dispatch({ type: 'SET_FORM_FIELD', name, value })}
          onSubmit={onSubmit}
        />

        <ReviewForm
          form={state.reviewForm}
          saving={state.reviewSaving}
          canReview={canReview}
          onChange={(name, value) => dispatch({ type: 'SET_REVIEW_FORM_FIELD', name, value })}
          onSubmit={onReviewSubmit}
        />
      </div>

      <JustificativosList
        justifications={justifications}
        loading={loading}
        saving={state.reviewSaving}
        canReview={canReview}
        onQuickReview={onQuickReview}
        onSelectForReview={(id) => dispatch({ type: 'SET_REVIEW_FORM_FIELD', name: 'justificativo_id', value: id })}
      />

      <DelayForm
        students={students}
        classes={classes}
        form={state.delayForm}
        saving={state.delaySaving}
        canCreate={canCreate}
        onChange={(name, value) => dispatch({ type: 'SET_DELAY_FORM_FIELD', name, value })}
        onSubmit={onDelaySubmit}
      />
    </section>
  );
}
