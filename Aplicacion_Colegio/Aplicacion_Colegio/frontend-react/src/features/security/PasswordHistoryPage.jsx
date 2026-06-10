import { useEffect, useMemo, useReducer } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';

import { useFetch } from '../../hooks';
import { apiClient } from '../../services/apiClient';
import { usePermissions } from '../../hooks/usePermissions';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { formatNumber } from '../../utils/formatters';



const initialState = {
  auditRows: [],
  periodDays: '7',
  modelFilter: '',
  loadingAudit: false,
  auditError: '',
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_FIELD':
      return { ...state, [action.payload.name]: action.payload.value };
    case 'START_AUDIT':
      return { ...state, loadingAudit: true, auditError: '' };
    case 'FINISH_AUDIT':
      return { ...state, loadingAudit: false, auditRows: action.payload };
    case 'ERROR_AUDIT':
      return { ...state, loadingAudit: false, auditError: action.payload, auditRows: [] };
    default:
      return state;
  }
}

export default function PasswordHistoryPage() {
  const me = useAuthStore((state) => state.user);

  const [state, dispatch] = useReducer(reducer, initialState);
  const { auditRows, periodDays, modelFilter, loadingAudit, auditError } = state;

  const { canAny } = usePermissions(me);
  const canView = canAny(['AUDIT_VIEW', 'SYSTEM_ADMIN']);

  const { data: passwordData, loading, error } = useFetch('/api/v1/seguridad/password-history/');

  // Derive rows inline from query data (no useEffect sync needed)
  const rows = Array.isArray(passwordData?.entries) ? passwordData.entries : [];

  const summaryCards = useMemo(() => {
    return [
      {
        title: 'Historial',
        value: rows.length,
        subtitle: rows.length > 0 ? 'Cambios de contrasena registrados' : 'Sin historial visible',
      },
      {
        title: 'Auditoria',
        value: auditRows.length,
        subtitle: auditRows.length > 0 ? 'Eventos sensibles detectados' : 'Sin eventos sensibles',
      },
      {
        title: 'Ventana',
        value: `${periodDays} días`,
        subtitle: 'Periodo consultado para la auditoria',
      },
      {
        title: 'Filtro modelo',
        value: modelFilter.trim() || 'Todos',
        subtitle: 'Modelo utilizado en la consulta',
      },
    ];
  }, [auditRows.length, modelFilter, periodDays, rows.length]);

  async function loadSensitiveAudit() {
    dispatch({ type: 'START_AUDIT' });
    try {
      const params = new URLSearchParams();
      if (periodDays) {
        params.set('dias', periodDays);
      }
      if (modelFilter.trim()) {
        params.set('modelo', modelFilter.trim());
      }
      const query = params.toString();
      const payload = await apiClient.get(`/api/v1/seguridad/auditoria-datos-sensibles/${query ? `?${query}` : ''}`);
      dispatch({ type: 'FINISH_AUDIT', payload: Array.isArray(payload?.eventos) ? payload.eventos : [] });
    } catch (err) {
      dispatch({ type: 'ERROR_AUDIT', payload: err.payload?.detail || 'No se pudo cargar la auditoria de datos sensibles.' });
    }
  }

  useEffect(() => {
    if (!canView) return;
    loadSensitiveAudit();
  }, [canView, periodDays, modelFilter]);

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="password-history-title">Seguridad: Password History</h2>
            <p>No tienes permisos para ver esta pagina.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>Seguridad: Password History</h2>
          <p>Auditoría de eventos de cambio de contraseña y accesos sensibles.</p>
        </div>
      </header>

      {error ? <div className="error-box" data-testid="password-history-error" role="alert" aria-live="assertive">{error}</div> : null}

      <div className="summary-grid" data-testid="password-history-summary">
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

      <article className="card section-card">
        <div className="section-card-head">
            <div>
              <h3>Historial de contraseñas</h3>
              <p>Registro de cambios de credenciales y metadatos visibles para auditoría.</p>
            </div>
          </div>

          {loading ? (
            <TableLoadingState />
          ) : (
            <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Usuario</th>
                  <th>Rol</th>
                  <th>RBD</th>
                  <th>Fecha Registro</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.user_email}</td>
                    <td>{row.user_rol || '-'}</td>
                    <td>{row.colegio_rbd || '-'}</td>
                    <td>{row.created_at}</td>
                  </tr>
                ))}
                {!rows.length ? (
                  <tr>
                    <td colSpan={5}>No hay registros de historial para mostrar.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
            </div>
          )}
        </article>

      <article className="card section-card">
        <h3>Auditoria de Datos Sensibles</h3>
        <div className="actions">
          <label>
            Dias
            <input
              type="number"
              min="1"
              max="90"
              value={periodDays}
              onChange={(e) => dispatch({ type: 'SET_FIELD', payload: { name: 'periodDays', value: e.target.value } })}
            />
          </label>
          <label>
            Modelo
            <input
              value={modelFilter}
              onChange={(e) => dispatch({ type: 'SET_FIELD', payload: { name: 'modelFilter', value: e.target.value } })}
              placeholder="Ej: PerfilEstudiante"
            />
          </label>
          <button type="button" className="secondary" onClick={loadSensitiveAudit}>
            Aplicar
          </button>
        </div>

        {auditError ? <div className="error-box section-card">{auditError}</div> : null}
        
        {loadingAudit ? (
          <TableLoadingState />
        ) : (
          <>
            {!auditError && auditRows.length === 0 ? (
              <p className="section-muted">No hay accesos sensibles en el periodo consultado.</p>
            ) : null}

            <div className="table-wrap section-card">
              <table>
                <thead>
                  <tr>
                <th>Fecha</th>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Modelo</th>
                <th>Object ID</th>
                <th>IP</th>
                <th>Campos</th>
              </tr>
            </thead>
            <tbody>
              {auditRows.map((row) => (
                <tr key={row.id}>
                  <td>{row.timestamp}</td>
                  <td>{row.usuario}</td>
                  <td>{row.rol || '-'}</td>
                  <td>{row.modelo || '-'}</td>
                  <td>{row.object_id || '-'}</td>
                  <td>{row.ip || '-'}</td>
                  <td>{Array.isArray(row.campos) && row.campos.length ? row.campos.join(', ') : '-'}</td>
                </tr>
              ))}
              {!auditRows.length && !loadingAudit ? (
                <tr>
                  <td colSpan={7}>No hay accesos sensibles para mostrar.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        </>
        )}
      </article>
    </section>
  );
}


