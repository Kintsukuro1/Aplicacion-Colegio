import { useEffect, useReducer, useRef } from 'react';

import SubscriptionStatusCard from '../../components/layout/SubscriptionStatusCard';
import { apiClient } from '../../services/apiClient';

const FEATURE_LABELS = {
  attendance: 'Asistencia',
  grades: 'Calificaciones',
  messaging: 'Mensajería',
  reports: 'Reportes',
  advanced_reports: 'Reportes Avanzados',
  attachments: 'Adjuntos',
  api_access: 'Acceso API',
  priority_support: 'Soporte Prioritario',
  branding: 'Marca personalizada',
};

function PlanCard({ plan, onContract, currentPlan }) {
  const isCurrent = currentPlan && plan.codigo === currentPlan;

  return (
    <article className={`pricing-card ${plan.destacado ? 'pricing-featured' : ''}`}>
      {plan.destacado ? (
        <span className="pricing-badge">⭐ Recomendado</span>
      ) : null}

      <div className="pricing-header">
        <h3>{plan.nombre}</h3>
        {plan.is_trial ? (
          <div className="pricing-price">
            <span className="pricing-amount">Gratis</span>
            <span className="pricing-period">30 días</span>
          </div>
        ) : plan.is_unlimited ? (
          <div className="pricing-price">
            <span className="pricing-amount">Demo</span>
            <span className="pricing-period">Ilimitado</span>
          </div>
        ) : (
          <div className="pricing-price">
            <span className="pricing-currency">$</span>
            <span className="pricing-amount">
              {parseInt(plan.precio_mensual).toLocaleString('es-CL')}
            </span>
            <span className="pricing-period">/mes</span>
          </div>
        )}
        <p className="pricing-desc">
          {plan.descripcion || 'Plan para colegios que quieren crecer sin fricción.'}
        </p>
      </div>

      <div className="pricing-limits">
        <div className="pricing-limit-item">
          <span>👥</span>
          <span>{plan.limites.estudiantes} estudiantes</span>
        </div>
        <div className="pricing-limit-item">
          <span>👨‍🏫</span>
          <span>{plan.limites.profesores} profesores</span>
        </div>
        <div className="pricing-limit-item">
          <span>📚</span>
          <span>{plan.limites.cursos} cursos</span>
        </div>
        <div className="pricing-limit-item">
          <span>💾</span>
          <span>{plan.limites.almacenamiento_mb} MB</span>
        </div>
      </div>

      <div className="pricing-features">
        {Object.entries(plan.features || {}).map(([key, enabled]) => (
          <div key={key} className={`pricing-feature ${enabled ? '' : 'disabled'}`}>
            <span>{enabled ? '✅' : '❌'}</span>
            <span>{FEATURE_LABELS[key] || key}</span>
          </div>
        ))}
      </div>

      <button
        type="button"
        className={`pricing-cta ${plan.destacado ? 'pricing-cta-primary' : ''}`}
        onClick={() => onContract(plan)}
        disabled={isCurrent || plan.is_unlimited}
      >
        {isCurrent
          ? '✓ Plan Actual'
          : plan.is_trial
            ? 'Comenzar Prueba'
            : plan.is_unlimited
              ? 'Solo Desarrollo'
              : 'Contratar'}
      </button>
    </article>
  );
}

const initialState = {
  plans: [],
  providers: [],
  selectedProvider: 'bank_transfer_bancoestado',
  status: null,
  loading: true,
  error: '',
  checkoutMessage: '',
  checkoutDetails: null,
  transferForm: { reference: '', amount: '', bank_name: '', account_holder: '', notes: '' },
};

function reducer(state, action) {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true, error: '' };
    case 'FETCH_SUCCESS': {
      const { plans, status, providers } = action.payload;
      const initialProvider = providers.find((p) => p.active) || providers[0];
      return {
        ...state,
        loading: false,
        plans,
        status,
        providers,
        selectedProvider: initialProvider?.codigo || state.selectedProvider,
      };
    }
    case 'FETCH_ERROR':
      return { ...state, loading: false, error: action.payload };
    case 'SET_PROVIDER':
      return { ...state, selectedProvider: action.payload };
    case 'CHECKOUT_START':
      return { ...state, checkoutMessage: '', checkoutDetails: null };
    case 'CHECKOUT_SUCCESS':
      return {
        ...state,
        checkoutDetails: action.payload.instructions,
        transferForm: {
          ...state.transferForm,
          amount: action.payload.instructions?.amount || state.transferForm.amount,
          reference: action.payload.instructions?.reference || state.transferForm.reference,
          bank_name: action.payload.instructions?.bank_name || state.transferForm.bank_name,
          account_holder: action.payload.instructions?.account_holder || state.transferForm.account_holder,
        },
      };
    case 'CHECKOUT_MESSAGE':
      return { ...state, checkoutMessage: action.payload };
    case 'UPDATE_TRANSFER_FORM':
      return { ...state, transferForm: { ...state.transferForm, ...action.payload } };
    default:
      return state;
  }
}

export default function PricingPage() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const lastPaymentIdRef = useRef(null);

  const {
    plans,
    providers,
    selectedProvider,
    status,
    loading,
    error,
    checkoutMessage,
    checkoutDetails,
    transferForm,
  } = state;

  useEffect(() => {
    let active = true;

    async function loadData() {
      dispatch({ type: 'FETCH_START' });
      try {
        const [plansResponse, dashboardResponse, providersResponse] = await Promise.all([
          apiClient.get('/api/v1/plans/'),
          apiClient.get('/api/v1/dashboard/resumen/?scope=school').catch(() => null),
          apiClient.get('/api/v1/payments/providers/').catch(() => ({ providers: [] })),
        ]);
        if (!active) return;
        dispatch({
          type: 'FETCH_SUCCESS',
          payload: {
            plans: plansResponse.plans || [],
            status: dashboardResponse,
            providers: providersResponse.providers || [],
          },
        });
      } catch (err) {
        if (active) {
          dispatch({ type: 'FETCH_ERROR', payload: err.payload?.detail || 'No se pudieron cargar los planes.' });
        }
      }
    }

    loadData();
    return () => {
      active = false;
    };
  }, []);

  async function handleContract(plan) {
    dispatch({ type: 'CHECKOUT_START' });
    lastPaymentIdRef.current = null;
    try {
      const response = await apiClient.post('/api/v1/payments/create-checkout/', {
        plan_codigo: plan.codigo,
        provider: selectedProvider,
      });
      lastPaymentIdRef.current = response?.payment_id || null;
      if (response?.instructions) {
        dispatch({ type: 'CHECKOUT_SUCCESS', payload: { instructions: response.instructions } });
      }
      if (response?.checkout_url && response.provider === 'webpay') {
        window.location.assign(response.checkout_url);
        return;
      }
      if (response?.checkout_url && response.provider === 'bank_transfer_bancoestado') {
        dispatch({ type: 'CHECKOUT_MESSAGE', payload: 'Se generaron las instrucciones de transferencia. Revisa los datos debajo y valida el pago desde el historial.' });
        return;
      }
      dispatch({ type: 'CHECKOUT_MESSAGE', payload: response?.detail || 'Checkout no disponible. Modo demo activo.' });
    } catch (err) {
      dispatch({ type: 'CHECKOUT_MESSAGE', payload: err.payload?.detail || 'No fue posible iniciar el checkout.' });
    }
  }

  async function handleTransferNotice() {
    if (!lastPaymentIdRef.current) {
      dispatch({ type: 'CHECKOUT_MESSAGE', payload: 'Primero crea el checkout para generar el pago asociado.' });
      return;
    }

    try {
      const response = await apiClient.post('/api/v1/payments/notify-transfer/', {
        payment_id: lastPaymentIdRef.current,
        ...transferForm,
      });
      dispatch({ type: 'CHECKOUT_MESSAGE', payload: response?.detail || 'Aviso de transferencia registrado.' });
    } catch (err) {
      dispatch({ type: 'CHECKOUT_MESSAGE', payload: err.payload?.detail || 'No fue posible registrar el aviso de transferencia.' });
    }
  }

  const currentPlanCode = status?.sections?.self?.plan_codigo;
  const currentPlanName = status?.sections?.self?.plan_actual;
  const currentStudents = status?.sections?.self?.total_estudiantes ?? 0;
  const currentMessages = status?.sections?.self?.comunicados_sin_leer ?? 0;

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="pricing-title">💎 Planes y Precios</h2>
          <p>Elige el plan que mejor se adapte a tu institución</p>
        </div>
      </header>

      {currentPlanName ? (
        <SubscriptionStatusCard
          planName={currentPlanName}
          daysRemaining={status?.sections?.self?.dias_restantes}
          studentsUsed={currentStudents}
          messagesUsed={currentMessages}
        />
      ) : null}

      {loading ? <div className="loading-dot" role="status" aria-live="polite" aria-label="Cargando"><span /><span /><span /></div> : null}
      {error ? <div className="error-box" data-testid="pricing-error" role="alert" aria-live="assertive">{error}</div> : null}
      {checkoutMessage ? <div className="error-box" role="alert" aria-live="assertive">{checkoutMessage}</div> : null}

      {!loading && providers.length > 0 ? (
        <section className="subscription-section">
          <h3>Medio de Pago</h3>
          <div className="payment-provider-picker">
            {providers.map((provider) => (
              <button
                key={provider.codigo}
                type="button"
                className={`provider-chip ${selectedProvider === provider.codigo ? 'active' : ''} ${provider.active ? '' : 'disabled'}`}
                onClick={() => provider.active && dispatch({ type: 'SET_PROVIDER', payload: provider.codigo })}
                disabled={!provider.active}
              >
                <strong>{provider.nombre}</strong>
                <span>{provider.descripcion}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {checkoutDetails ? (
        <section className="subscription-section">
          <h3>Instrucciones de Pago</h3>
          <div className="payment-instructions-card">
            {checkoutDetails.bank_name ? <p><strong>Banco:</strong> {checkoutDetails.bank_name}</p> : null}
            {checkoutDetails.account_holder ? <p><strong>Titular:</strong> {checkoutDetails.account_holder}</p> : null}
            {checkoutDetails.account_type ? <p><strong>Tipo de cuenta:</strong> {checkoutDetails.account_type}</p> : null}
            {checkoutDetails.account_number ? <p><strong>Número:</strong> {checkoutDetails.account_number}</p> : null}
            {checkoutDetails.account_rut ? <p><strong>RUT:</strong> {checkoutDetails.account_rut}</p> : null}
            {checkoutDetails.reference ? <p><strong>Referencia:</strong> {checkoutDetails.reference}</p> : null}
            {Array.isArray(checkoutDetails.instructions) ? (
              <ul className="payment-instructions-list">
                {checkoutDetails.instructions.map((instruction) => (
                  <li key={instruction}>{instruction}</li>
                ))}
              </ul>
            ) : null}
            {selectedProvider === 'bank_transfer_bancoestado' ? (
              <div className="transfer-notice-form">
                <label>
                  Referencia
                  <input value={transferForm.reference} onChange={(event) => dispatch({ type: 'UPDATE_TRANSFER_FORM', payload: { reference: event.target.value } })} placeholder="Referencia del comprobante" />
                </label>
                <label>
                  Monto
                  <input value={transferForm.amount} onChange={(event) => dispatch({ type: 'UPDATE_TRANSFER_FORM', payload: { amount: event.target.value } })} placeholder="Monto transferido" />
                </label>
                <label>
                  Banco
                  <input value={transferForm.bank_name} onChange={(event) => dispatch({ type: 'UPDATE_TRANSFER_FORM', payload: { bank_name: event.target.value } })} placeholder="Banco emisior" />
                </label>
                <label>
                  Titular
                  <input value={transferForm.account_holder} onChange={(event) => dispatch({ type: 'UPDATE_TRANSFER_FORM', payload: { account_holder: event.target.value } })} placeholder="Titular de la cuenta" />
                </label>
                <label>
                  Observaciones
                  <textarea value={transferForm.notes} onChange={(event) => dispatch({ type: 'UPDATE_TRANSFER_FORM', payload: { notes: event.target.value } })} rows="3" placeholder="Nombre del apoderado, fecha, sucursal, etc." />
                </label>
                <button type="button" onClick={handleTransferNotice} className="pricing-cta pricing-cta-primary">
                  Registrar aviso de transferencia
                </button>
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      {!loading && plans.length > 0 ? (
        <div className="pricing-grid">
          {plans.map((plan) => (
            <PlanCard
              key={plan.codigo}
              plan={plan}
              onContract={handleContract}
              currentPlan={currentPlanCode}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
