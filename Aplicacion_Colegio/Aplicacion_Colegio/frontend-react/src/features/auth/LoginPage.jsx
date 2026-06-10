import { useMemo, useReducer } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { apiClient } from '../../services/apiClient';
import { setTokens } from '../../stores/authStore';
import { useTenant } from '../../utils/tenantContext';

const initialState = {
  email: '',
  password: '',
  loading: false,
  error: '',
  touched: { email: false, password: false },
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_FIELD':
      return { ...state, [action.payload.name]: action.payload.value, error: '' };
    case 'SET_TOUCHED':
      return { ...state, touched: { ...state.touched, [action.payload]: true } };
    case 'TOUCH_ALL':
      return { ...state, touched: { email: true, password: true } };
    case 'START_SUBMIT':
      return { ...state, loading: true, error: '' };
    case 'SET_ERROR':
      return { ...state, loading: false, error: action.payload };
    case 'FINISH_SUBMIT':
      return { ...state, loading: false };
    default:
      return state;
  }
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { tenant } = useTenant();

  const [state, dispatch] = useReducer(reducer, initialState);
  const { email, password, loading, error, touched } = state;

  const emailError = useMemo(() => {
    if (!touched.email) {
      return '';
    }

    const value = email.trim();
    if (!value) {
      return 'Ingresa tu correo institucional.';
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      return 'Ingresa un correo válido.';
    }

    return '';
  }, [email, touched.email]);

  const passwordError = useMemo(() => {
    if (!touched.password) {
      return '';
    }

    if (!password.trim()) {
      return 'Ingresa tu contraseña.';
    }

    return '';
  }, [password, touched.password]);

  const canSubmit = Boolean(!loading && !emailError && !passwordError && email.trim() && password.trim());

  function getRedirectTarget() {
    const fromPath = location.state?.from?.pathname;
    return fromPath && fromPath !== '/login' ? fromPath : '/dashboard';
  }

  async function onSubmit(event) {
    event.preventDefault();
    dispatch({ type: 'SET_ERROR', payload: '' });

    dispatch({ type: 'TOUCH_ALL' });

    if (!email.trim() || !password.trim()) {
      return;
    }

    if (emailError || passwordError) {
      return;
    }

    dispatch({ type: 'START_SUBMIT' });

    try {
      const payload = await apiClient.post('/api/v1/auth/token/', { email: email.trim().toLowerCase(), password });
      setTokens({ access: payload.access, refresh: payload.refresh });
      navigate(getRedirectTarget(), { replace: true });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.payload?.detail || 'No se pudo iniciar sesion.' });
    } finally {
      dispatch({ type: 'FINISH_SUBMIT' });
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <div className="auth-logo">
          {tenant?.logo ? (
            <img src={tenant.logo} alt={`Logo ${tenant.nombre}`} className="tenant-logo" />
          ) : (
            <span className="auth-logo-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
            </span>
          )}
          <span className="brand-text">{tenant?.nombre || 'Colegio SaaS'}</span>
        </div>

        <h1>Acceso a la plataforma</h1>
        <p>Ingresa tus credenciales para acceder al sistema de gestión.</p>

        <label>
          Correo
          <input
            type="email"
            value={email}
            onChange={(e) => dispatch({ type: 'SET_FIELD', payload: { name: 'email', value: e.target.value } })}
            onBlur={() => dispatch({ type: 'SET_TOUCHED', payload: 'email' })}
            required
            autoComplete="username"
            placeholder="correo@ejemplo.cl"
            aria-invalid={Boolean(emailError || error)}
            aria-describedby={emailError ? 'login-email-error' : undefined}
          />
          {emailError ? <small id="login-email-error" className="field-error">{emailError}</small> : null}
        </label>

        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(e) => dispatch({ type: 'SET_FIELD', payload: { name: 'password', value: e.target.value } })}
            onBlur={() => dispatch({ type: 'SET_TOUCHED', payload: 'password' })}
            required
            autoComplete="current-password"
            placeholder="••••••••"
            aria-invalid={Boolean(passwordError || error)}
            aria-describedby={passwordError ? 'login-password-error' : undefined}
          />
          {passwordError ? <small id="login-password-error" className="field-error">{passwordError}</small> : null}
        </label>

        {error ? <div className="error-box" data-testid="login-error" role="alert" aria-live="assertive">{error}</div> : null}

        <button type="submit" disabled={!canSubmit} aria-busy={loading}>
          {loading ? 'Ingresando...' : 'Ingresar'}
        </button>

        <div className="register-link">
          ¿Eres un colegio nuevo?{' '}
          <Link to="/register">Registra tu institución</Link>
        </div>
      </form>
    </div>
  );
}

