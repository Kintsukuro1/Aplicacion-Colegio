import { useEffect, useReducer, useState } from 'react';

import { apiClient } from '../../services/apiClient';
import { getAccessToken } from '../../stores/authStore';

async function downloadWithAuth(path, fallbackName) {
  const access = getAccessToken();
  const headers = {};
  if (access) {
    headers.Authorization = `Bearer ${access}`;
  }

  const response = await fetch(`${apiClient.baseUrl}${path}`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail || 'No se pudo descargar el archivo.');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fallbackName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export default function TransferNoticesPage() {
  const [state, dispatch] = useReducer(
    (current, action) => {
      switch (action.type) {
        case 'loading':
          return { ...current, loading: true, error: '' };
        case 'loaded':
          return { ...current, loading: false, notices: action.notices, error: '' };
        case 'error':
          return { ...current, loading: false, error: action.error };
        case 'message':
          return { ...current, message: action.message };
        default:
          return current;
      }
    },
    {
      notices: [],
      loading: true,
      error: '',
      message: '',
    },
  );
  const { notices, loading, error, message } = state;
  const [filters, setFilters] = useState({
    status: 'pending',
    gateway: 'bank_transfer_bancoestado',
    since: '',
    until: '',
  });

  async function loadNotices() {
    dispatch({ type: 'loading' });
    try {
      const params = new URLSearchParams();
      if (filters.status) params.set('status', filters.status);
      if (filters.gateway) params.set('gateway', filters.gateway);
      if (filters.since) params.set('since', filters.since);
      if (filters.until) params.set('until', filters.until);
      const response = await apiClient.get(`/api/v1/payments/transfer-notices/?${params.toString()}`);
      dispatch({ type: 'loaded', notices: response.notices || [] });
    } catch (err) {
      dispatch({
        type: 'error',
        error: err.payload?.detail || 'No se pudieron cargar los avisos de transferencia.',
      });
    }
  }

  useEffect(() => {
    loadNotices();
  }, [filters]);

  async function handleApprove(paymentId) {
    dispatch({ type: 'message', message: '' });
    try {
      const response = await apiClient.post('/api/v1/payments/transfer-notices/approve/', { payment_id: paymentId });
      dispatch({ type: 'message', message: response?.detail || 'Transferencia aprobada.' });
      await loadNotices();
    } catch (err) {
      dispatch({ type: 'message', message: err.payload?.detail || 'No se pudo aprobar la transferencia.' });
    }
  }

  async function handleExport() {
    dispatch({ type: 'message', message: '' });
    try {
      const params = new URLSearchParams();
      if (filters.status) params.set('status', filters.status);
      if (filters.gateway) params.set('gateway', filters.gateway);
      if (filters.since) params.set('since', filters.since);
      if (filters.until) params.set('until', filters.until);
      await downloadWithAuth(`/api/v1/payments/transfer-notices/export/?${params.toString()}`, 'transferencias_pendientes.csv');
      dispatch({ type: 'message', message: 'Exportación descargada.' });
    } catch (err) {
      dispatch({ type: 'message', message: err.message || 'No se pudo exportar el listado.' });
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="transfer-notices-title">Transferencias Bancarias</h2>
          <p>Revisa y concilia los comprobantes enviados por los colegios.</p>
        </div>
      </header>

      {loading ? <div className="loading-dot" role="status" aria-live="polite" aria-label="Cargando"><span /><span /><span /></div> : null}
      {error ? <div className="error-box" data-testid="transfer-notices-error" role="alert" aria-live="assertive">{error}</div> : null}
      {message ? <div className="error-box" role="alert" aria-live="assertive">{message}</div> : null}

      <div className="transfer-notices-filters">
        <label>
          Estado
          <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}>
            <option value="">Todos</option>
            <option value="pending">Pendiente</option>
            <option value="approved">Aprobado</option>
            <option value="rejected">Rechazado</option>
          </select>
        </label>
        <label>
          Proveedor
          <select value={filters.gateway} onChange={(event) => setFilters((current) => ({ ...current, gateway: event.target.value }))}>
            <option value="">Todos</option>
            <option value="bank_transfer_bancoestado">BancoEstado</option>
            <option value="bank_transfer">Transferencia</option>
            <option value="webpay">Webpay</option>
            <option value="mercadopago">MercadoPago</option>
          </select>
        </label>
        <label>
          Desde
          <input type="date" value={filters.since} onChange={(event) => setFilters((current) => ({ ...current, since: event.target.value }))} />
        </label>
        <label>
          Hasta
          <input type="date" value={filters.until} onChange={(event) => setFilters((current) => ({ ...current, until: event.target.value }))} />
        </label>
      </div>

      <div className="subscription-section-actions">
        <button type="button" className="secondary" onClick={handleExport}>
          Exportar CSV
        </button>
      </div>

      {!loading && notices.length > 0 ? (
        <div className="transfer-notices-grid">
          {notices.map((notice) => (
            <article key={notice.payment_id} className="transfer-notice-card">
              <div className="transfer-notice-card-head">
                <strong>{notice.plan}</strong>
                <span className={`badge badge-${notice.status}`}>{notice.status}</span>
              </div>
              <p><strong>Referencia:</strong> {notice.notice?.reference || '-'}</p>
              <p><strong>Monto:</strong> {notice.moneda} {notice.monto}</p>
              <p><strong>Banco:</strong> {notice.notice?.bank_name || '-'}</p>
              <p><strong>Titular:</strong> {notice.notice?.account_holder || '-'}</p>
              <p><strong>Observaciones:</strong> {notice.notice?.notes || '-'}</p>
              <button type="button" className="pricing-cta pricing-cta-primary" onClick={() => handleApprove(notice.payment_id)}>
                Aprobar conciliación
              </button>
            </article>
          ))}
        </div>
      ) : null}

      {!loading && notices.length === 0 ? (
        <div className="empty-state">
          No hay transferencias pendientes por revisar.
        </div>
      ) : null}
    </section>
  );
}
