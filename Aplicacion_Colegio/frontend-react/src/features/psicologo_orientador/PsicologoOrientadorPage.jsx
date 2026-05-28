import { useMemo, useReducer } from 'react';

import { apiClient } from '../../services/apiClient';
import { useQuery } from '@tanstack/react-query';
import { hasCapability } from '../../utils/capabilities';
import { useToast } from '../../components/feedback/Toast';
import { useAuthStore } from '../../stores/useAuthStore';

import { InterviewForm } from './InterviewForm';
import { ReferralForm } from './ReferralForm';
import { UpdateReferralForm } from './UpdateReferralForm';
import { PieForm } from './PieForm';

const EMPTY_INTERVIEW_FORM = {
  estudiante_id: '',
  fecha: '',
  motivo: 'ACADEMICO',
  observaciones: '',
  acuerdos: '',
  seguimiento_requerido: false,
};

const EMPTY_REFERRAL_FORM = {
  estudiante_id: '',
  profesional_destino: '',
  especialidad: '',
  motivo: '',
  fecha_derivacion: '',
};

const EMPTY_UPDATE_REFERRAL_FORM = {
  derivacion_id: '',
  estado: 'EN_PROCESO',
  informe_retorno: '',
  fecha_retorno: '',
};

const EMPTY_PIE_FORM = {
  estudiante_id: '',
  requiere_pie: true,
};

function resolveError(err, fallback) {
  return err?.payload?.error || err?.payload?.detail || fallback;
}

const initialState = {
  form: EMPTY_INTERVIEW_FORM,
  referralForm: EMPTY_REFERRAL_FORM,
  updateReferralForm: EMPTY_UPDATE_REFERRAL_FORM,
  pieForm: EMPTY_PIE_FORM,
  saving: false,
  referralSaving: false,
  updateReferralSaving: false,
  pieSaving: false,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_FORM_FIELD':
      return { ...state, form: { ...state.form, [action.name]: action.value } };
    case 'SET_REFERRAL_FIELD':
      return { ...state, referralForm: { ...state.referralForm, [action.name]: action.value } };
    case 'SET_UPDATE_REFERRAL_FIELD':
      return { ...state, updateReferralForm: { ...state.updateReferralForm, [action.name]: action.value } };
    case 'SET_PIE_FIELD':
      return { ...state, pieForm: { ...state.pieForm, [action.name]: action.value } };
    case 'RESET_FORM':
      return { ...state, form: EMPTY_INTERVIEW_FORM };
    case 'RESET_REFERRAL_FORM':
      return { ...state, referralForm: EMPTY_REFERRAL_FORM };
    case 'RESET_UPDATE_REFERRAL_FORM':
      return { ...state, updateReferralForm: EMPTY_UPDATE_REFERRAL_FORM };
    case 'RESET_PIE_FORM':
      return { ...state, pieForm: EMPTY_PIE_FORM };
    case 'SET_SAVING':
      return { ...state, [action.field]: action.value };
    default:
      return state;
  }
}

function PsicologoOrientadorLoadingState() {
  return (
    <article className="card section-card" aria-busy="true" aria-live="polite" role="status">
      <div style={{ height: '18px', width: '220px', borderRadius: '999px', background: 'rgba(148, 163, 184, 0.18)', marginBottom: '0.75rem' }} />
      <div style={{ height: '14px', width: '280px', borderRadius: '999px', background: 'rgba(148, 163, 184, 0.12)' }} />

      <div className="summary-grid" style={{ marginTop: '1.25rem' }}>
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="summary-tile" style={{ minHeight: '96px', background: 'rgba(148, 163, 184, 0.08)' }}>
            <div style={{ height: '12px', width: '92px', borderRadius: '999px', background: 'rgba(148, 163, 184, 0.18)', marginBottom: '0.85rem' }} />
            <div style={{ height: '24px', width: index === 0 ? '76px' : '92px', borderRadius: '12px', background: 'rgba(148, 163, 184, 0.14)' }} />
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ marginTop: '1.25rem' }}>
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="card section-card" style={{ minHeight: '240px', background: 'rgba(148, 163, 184, 0.06)' }} />
        ))}
      </div>
    </article>
  );
}

export default function PsicologoOrientadorPage() {
  const me = useAuthStore((state) => state.user);
  const toast = useToast();
  const [state, dispatch] = useReducer(reducer, initialState);

  const { data: studentsData, isLoading: loading, error: errorObj } = useQuery({
    queryKey: ['psicologo-estudiantes'],
    queryFn: () => apiClient.get('/api/psicologo/estudiantes/')
  });
  const students = studentsData?.estudiantes || [];
  const error = errorObj ? resolveError(errorObj, 'No se pudo cargar estudiantes.') : '';

  const canCreate = useMemo(() => hasCapability(me, 'COUNSELING_CREATE') || hasCapability(me, 'SYSTEM_ADMIN'), [me]);
  const canCreateReferral = useMemo(
    () => hasCapability(me, 'REFERRAL_CREATE') || hasCapability(me, 'SYSTEM_ADMIN'),
    [me]
  );
  const canEditReferral = useMemo(
    () => hasCapability(me, 'REFERRAL_EDIT') || hasCapability(me, 'SYSTEM_ADMIN'),
    [me]
  );

  const summaryCards = useMemo(
    () => [
      {
        title: 'Estudiantes cargados',
        value: students.length,
        subtitle: students.length > 0 ? 'Disponibles para intervención' : 'Sin estudiantes cargados',
      },
      {
        title: 'Entrevistas',
        value: canCreate ? 'Activo' : 'Bloqueado',
        subtitle: 'Registro de orientación',
      },
      {
        title: 'Derivaciones',
        value: canCreateReferral || canEditReferral ? 'Activo' : 'Bloqueado',
        subtitle: canEditReferral ? 'Crear y actualizar derivaciones' : 'Solo lectura de derivaciones',
      },
      {
        title: 'Estado panel',
        value: loading ? 'Cargando' : 'Listo',
        subtitle: loading ? 'Esperando estudiantes' : 'Panel operativo',
      },
    ],
    [canCreate, canCreateReferral, canEditReferral, loading, students.length]
  );

  async function onSubmit(event) {
    event.preventDefault();
    if (!canCreate) {
      toast.error('No tienes permisos para crear entrevistas.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'saving', value: true });
    try {
      const payload = await apiClient.post('/api/psicologo/entrevistas/crear/', {
        estudiante_id: Number(state.form.estudiante_id),
        fecha: state.form.fecha,
        motivo: state.form.motivo,
        observaciones: state.form.observaciones,
        acuerdos: state.form.acuerdos,
        seguimiento_requerido: Boolean(state.form.seguimiento_requerido),
      });
      toast.success(payload?.message || 'Entrevista creada.');
      dispatch({ type: 'RESET_FORM' });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo crear la entrevista.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'saving', value: false });
    }
  }

  async function onReferralSubmit(event) {
    event.preventDefault();
    if (!canCreateReferral) {
      toast.error('No tienes permisos para crear derivaciones.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'referralSaving', value: true });
    try {
      const payload = await apiClient.post('/api/psicologo/derivaciones/crear/', {
        estudiante_id: Number(state.referralForm.estudiante_id),
        profesional_destino: state.referralForm.profesional_destino,
        especialidad: state.referralForm.especialidad,
        motivo: state.referralForm.motivo,
        fecha_derivacion: state.referralForm.fecha_derivacion || undefined,
      });
      toast.success(payload?.message || 'Derivacion registrada.');
      dispatch({ type: 'RESET_REFERRAL_FORM' });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo crear la derivacion.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'referralSaving', value: false });
    }
  }

  async function onUpdateReferralSubmit(event) {
    event.preventDefault();
    if (!canEditReferral) {
      toast.error('No tienes permisos para editar derivaciones.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'updateReferralSaving', value: true });
    try {
      const payload = await apiClient.post(`/api/psicologo/derivaciones/${state.updateReferralForm.derivacion_id}/`, {
        estado: state.updateReferralForm.estado,
        informe_retorno: state.updateReferralForm.informe_retorno,
        fecha_retorno: state.updateReferralForm.fecha_retorno || undefined,
      });
      toast.success(payload?.message || 'Derivacion actualizada.');
      dispatch({ type: 'RESET_UPDATE_REFERRAL_FORM' });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo actualizar la derivacion.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'updateReferralSaving', value: false });
    }
  }

  async function onPieSubmit(event) {
    event.preventDefault();
    if (!canCreate) {
      toast.error('No tienes permisos para gestionar estado PIE.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'pieSaving', value: true });
    try {
      const payload = await apiClient.post(`/api/psicologo/estudiantes/${state.pieForm.estudiante_id}/pie/`, {
        requiere_pie: Boolean(state.pieForm.requiere_pie),
      });
      toast.success(payload?.message || 'Estado PIE actualizado.');
      dispatch({ type: 'RESET_PIE_FORM' });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo actualizar estado PIE.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'pieSaving', value: false });
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="psicologo-orientador-title">Psicologo Orientador</h2>
          <p>Registro rapido de entrevistas de orientacion.</p>
        </div>
      </header>

      {loading ? <PsicologoOrientadorLoadingState /> : null}
      {error ? <div className="error-box" data-testid="psicologo-orientador-error" role="alert" aria-live="assertive">{error}</div> : null}

      {!loading && !error ? (
        <div className="summary-grid" data-testid="psicologo-orientador-summary">
          {summaryCards.map((item) => (
            <article key={item.title} className="summary-tile">
              <small>{item.title}</small>
              <strong>{item.value}</strong>
              <span>{item.subtitle}</span>
            </article>
          ))}
        </div>
      ) : null}

      {!loading && !error && students.length === 0 ? <p className="section-muted">No hay estudiantes disponibles para orientar.</p> : null}

      <div className="grid-2">
        <InterviewForm
          students={students}
          form={state.form}
          saving={state.saving}
          canCreate={canCreate}
          onChange={(name, value) => dispatch({ type: 'SET_FORM_FIELD', name, value })}
          onSubmit={onSubmit}
        />

        <ReferralForm
          students={students}
          form={state.referralForm}
          saving={state.referralSaving}
          canCreateReferral={canCreateReferral}
          onChange={(name, value) => dispatch({ type: 'SET_REFERRAL_FIELD', name, value })}
          onSubmit={onReferralSubmit}
        />
      </div>

      <div className="grid-2">
        <UpdateReferralForm
          form={state.updateReferralForm}
          saving={state.updateReferralSaving}
          canEditReferral={canEditReferral}
          onChange={(name, value) => dispatch({ type: 'SET_UPDATE_REFERRAL_FIELD', name, value })}
          onSubmit={onUpdateReferralSubmit}
        />

        <PieForm
          students={students}
          form={state.pieForm}
          saving={state.pieSaving}
          canCreate={canCreate}
          onChange={(name, value) => dispatch({ type: 'SET_PIE_FIELD', name, value })}
          onSubmit={onPieSubmit}
        />
      </div>
    </section>
  );
}
