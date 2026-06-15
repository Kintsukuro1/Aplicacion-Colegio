import { useMemo, useReducer } from 'react';
import { useNavigate } from 'react-router-dom';

import OnboardingWizard from '../../components/utils/OnboardingWizard';
import { apiClient } from '../../services/apiClient';
import { setTokens } from '../../stores/authStore';

const STEPS = ['Admin', 'Colegio', 'Configuración', 'Confirmar'];

const initialState = {
  currentStep: 0,
  loading: false,
  error: '',
  available: null,
  form: {
    admin_name: '',
    admin_last_name: '',
    admin_email: '',
    admin_password: '',
    school_name: '',
    school_rut: '',
    school_email: '',
    school_phone: '',
    school_address: '',
    slug: '',
    color_primario: '#6366f1',
    school_year: new Date().getFullYear(),
    regimen_evaluacion: 'SEMESTRAL',
    nota_minima: 1.0,
    nota_maxima: 7.0,
    nota_aprobacion: 4.0,
    redondeo_decimales: 1,
    umbral_inasistencia_alerta: 3,
    umbral_notas_alerta: 4.0,
    generate_demo_data: false,
  },
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, currentStep: action.payload };
    case 'SET_LOADING':
      return { ...state, loading: action.payload, error: action.payload ? '' : state.error };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'SET_AVAILABLE':
      return { ...state, available: action.payload };
    case 'UPDATE_FORM':
      return { ...state, form: { ...state.form, [action.payload.field]: action.payload.value }, error: '' };
    default:
      return state;
  }
}

export default function RegisterPage() {
  const navigate = useNavigate();
  const [state, dispatch] = useReducer(reducer, initialState);
  const { currentStep, loading, error, available, form } = state;

  const stepSummary = useMemo(() => ({
    admin: form.admin_name && form.admin_email,
    school: form.school_name,
    config: form.regimen_evaluacion,
  }), [form]);

  function updateField(field, value) {
    dispatch({ type: 'UPDATE_FORM', payload: { field, value } });
  }

  async function checkSlug() {
    if (!form.slug) return;
    try {
      const response = await apiClient.get(`/api/v1/onboarding/check-slug/?slug=${encodeURIComponent(form.slug)}`);
      dispatch({ type: 'SET_AVAILABLE', payload: response.available });
    } catch {
      dispatch({ type: 'SET_AVAILABLE', payload: null });
    }
  }

  async function submit() {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await apiClient.post('/api/v1/onboarding/register/', form);
      try {
        const tokenPayload = await apiClient.post('/api/v1/auth/token/', {
          email: response.admin_email || form.admin_email,
          password: form.admin_password,
        });
        setTokens({ access: tokenPayload.access, refresh: tokenPayload.refresh });
        navigate('/dashboard', {
          replace: true,
          state: {
            onboardingComplete: true,
            schoolName: form.school_name,
            schoolSlug: response.colegio_slug,
            demoDataEnabled: Boolean(form.generate_demo_data),
          },
        });
        return;
      } catch {
        navigate('/login', {
          replace: true,
          state: {
            onboarding: response,
            createdEmail: response.admin_email,
          },
        });
      }
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.payload?.detail || 'No se pudo completar el registro.' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-card auth-card-wide">
        <header className="page-header">
          <div>
            <h2 data-testid="register-title">Crear mi colegio</h2>
            <p>Completa los datos básicos y tendrás tu colegio listo en minutos.</p>
          </div>
        </header>

        <OnboardingWizard steps={STEPS} currentStep={currentStep} />

        {currentStep === 0 ? (
          <div className="grid-2">
            <label>
              Nombre Admin
              <input value={form.admin_name} onChange={(e) => updateField('admin_name', e.target.value)} />
            </label>
            <label>
              Apellido Admin
              <input value={form.admin_last_name} onChange={(e) => updateField('admin_last_name', e.target.value)} />
            </label>
            <label>
              Email Admin
              <input type="email" value={form.admin_email} onChange={(e) => updateField('admin_email', e.target.value)} />
            </label>
            <label>
              Contraseña
              <input type="password" value={form.admin_password} onChange={(e) => updateField('admin_password', e.target.value)} />
            </label>
          </div>
        ) : null}

        {currentStep === 1 ? (
          <div className="grid-2">
            <label>
              RBD
              <input value={form.rbd || ''} onChange={(e) => updateField('rbd', e.target.value)} />
            </label>
            <label>
              Nombre del colegio
              <input value={form.school_name} onChange={(e) => updateField('school_name', e.target.value)} />
            </label>
            <label>
              Slug
              <input
                value={form.slug}
                onChange={(e) => updateField('slug', e.target.value)}
                onBlur={checkSlug}
                placeholder="mi-colegio"
              />
            </label>
            <label>
              Color principal
              <input type="color" value={form.color_primario} onChange={(e) => updateField('color_primario', e.target.value)} />
            </label>
          </div>
        ) : null}

        {currentStep === 2 ? (
          <div className="grid-2">
            <label>
              Régimen
              <select value={form.regimen_evaluacion} onChange={(e) => updateField('regimen_evaluacion', e.target.value)}>
                <option value="SEMESTRAL">Semestral</option>
                <option value="TRIMESTRAL">Trimestral</option>
                <option value="ANUAL">Anual</option>
              </select>
            </label>
            <label>
              Año escolar
              <input type="number" value={form.school_year} onChange={(e) => updateField('school_year', e.target.value)} />
            </label>
            <label>
              Aprobación
              <input type="number" step="0.1" value={form.nota_aprobacion} onChange={(e) => updateField('nota_aprobacion', e.target.value)} />
            </label>
            <label>
              <span>Generar datos demo</span>
              <input type="checkbox" checked={form.generate_demo_data} onChange={(e) => updateField('generate_demo_data', e.target.checked)} />
            </label>
          </div>
        ) : null}

        {currentStep === 3 ? (
          <article className="card section-card">
            <h3>Resumen</h3>
            <p><strong>Admin:</strong> {stepSummary.admin ? form.admin_name : 'Pendiente'}</p>
            <p><strong>Colegio:</strong> {stepSummary.school || 'Pendiente'}</p>
            <p><strong>Régimen:</strong> {stepSummary.config}</p>
            <p><strong>Slug:</strong> {form.slug || 'Pendiente'} {available === true ? '(disponible)' : available === false ? '(ocupado)' : ''}</p>
          </article>
        ) : null}

        {error ? <div className="error-box" data-testid="register-error" role="alert" aria-live="assertive">{error}</div> : null}

        <div className="subscription-status-actions">
          {currentStep > 0 ? (
            <button type="button" className="pricing-cta" onClick={() => dispatch({ type: 'SET_STEP', payload: Math.max(0, currentStep - 1) })}>
              Atrás
            </button>
          ) : null}
          {currentStep < STEPS.length - 1 ? (
            <button type="button" className="pricing-cta" onClick={() => dispatch({ type: 'SET_STEP', payload: currentStep + 1 })}>
              Siguiente
            </button>
          ) : (
            <button type="button" className="pricing-cta" onClick={submit} disabled={loading}>
              {loading ? 'Creando...' : 'Crear colegio'}
            </button>
          )}
        </div>
      </div>
    </section>
  );
}

