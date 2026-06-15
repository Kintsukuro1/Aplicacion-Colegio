import { useEffect, useReducer } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';

import { apiClient } from '../../services/apiClient';
import { usePermissions } from '../../hooks/usePermissions';

const STATES = ['pendiente', 'confirmada', 'reprogramada', 'rechazada', 'completada', 'cancelada'];
const TYPES = ['academica', 'conductual', 'orientacion', 'administrativa', 'general'];

const initialState = {
  rows: [],
  loading: false,
  savingId: null,
  error: '',
  filters: { estado: '', tipo: '' },
  responseText: {},
  newDate: {},
  newTime: {},
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload, error: '' };
    case 'SET_ROWS':
      return { ...state, rows: action.payload, loading: false };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false, savingId: null };
    case 'SET_SAVING_ID':
      return { ...state, savingId: action.payload, error: '' };
    case 'SET_FILTER':
      return { ...state, filters: { ...state.filters, [action.payload.name]: action.payload.value } };
    case 'SET_RESPONSE_TEXT':
      return { ...state, responseText: { ...state.responseText, [action.payload.id]: action.payload.value } };
    case 'SET_NEW_DATE':
      return { ...state, newDate: { ...state.newDate, [action.payload.id]: action.payload.value } };
    case 'SET_NEW_TIME':
      return { ...state, newTime: { ...state.newTime, [action.payload.id]: action.payload.value } };
    default:
      return state;
  }
}

export default function MeetingRequestsPage() {
  const me = useAuthStore((state) => state.user);
  
  const [state, dispatch] = useReducer(reducer, initialState);
  const { rows, loading, savingId, error, filters, responseText, newDate, newTime } = state;

  const { canAny } = usePermissions(me);
  const canView = canAny(['CLASS_VIEW', 'SYSTEM_CONFIGURE', 'SYSTEM_ADMIN']);
  const canRespond = canAny(['CLASS_VIEW', 'SYSTEM_CONFIGURE', 'SYSTEM_ADMIN']);

  async function loadRows() {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const params = new URLSearchParams();
      if (filters.estado) params.set('estado', filters.estado);
      if (filters.tipo) params.set('tipo', filters.tipo);
      const payload = await apiClient.get(`/api/v1/reuniones/mis-reuniones/?${params.toString()}`);
      dispatch({ type: 'SET_ROWS', payload: Array.isArray(payload?.reuniones) ? payload.reuniones : [] });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.payload?.detail || 'No se pudieron cargar las reuniones.' });
      dispatch({ type: 'SET_ROWS', payload: [] });
    }
  }

  useEffect(() => {
    if (!canView) return;
    loadRows();
  }, [canView]);

  async function respond(row, action) {
    if (!canRespond) {
      dispatch({ type: 'SET_ERROR', payload: 'No tienes permisos para responder reuniones.' });
      return;
    }

    const payload = {
      accion: action,
      respuesta_profesor: responseText[row.id] || '',
    };
    if (action === 'proponer_fecha') {
      payload.fecha_confirmada = newDate[row.id] || '';
      payload.hora_confirmada = newTime[row.id] || '';
      if (!payload.fecha_confirmada || !payload.hora_confirmada) {
        dispatch({ type: 'SET_ERROR', payload: 'Debes indicar fecha y hora para reprogramar.' });
        return;
      }
    }

    dispatch({ type: 'SET_SAVING_ID', payload: row.id });
    try {
      await apiClient.post(`/api/v1/reuniones/${row.id}/responder/`, payload);
      await loadRows();
      dispatch({ type: 'SET_SAVING_ID', payload: null });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo responder la reunion.' });
    }
  }

  async function cancelMeeting(row) {
    if (!window.confirm(`Cancelar reunion #${row.id}?`)) {
      return;
    }

    dispatch({ type: 'SET_SAVING_ID', payload: row.id });
    try {
      await apiClient.post(`/api/v1/reuniones/${row.id}/cancelar/`, {
        motivo: responseText[row.id] || '',
      });
      await loadRows();
      dispatch({ type: 'SET_SAVING_ID', payload: null });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err.payload?.detail || JSON.stringify(err.payload || {}) || 'No se pudo cancelar la reunion.' });
    }
  }

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="meeting-requests-title">Solicitudes de Reunion</h2>
            <p>No tienes permisos para ver esta bandeja.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>Solicitudes de Reunion</h2>
          <p>Bandeja para revisar, responder y cancelar reuniones.</p>
        </div>
      </header>

      {error ? <div className="error-box" data-testid="meeting-requests-error" role="alert" aria-live="assertive">{error}</div> : null}

      <div className="card form-grid">
        <h3 className="full">Filtros</h3>
        <label>
          Estado
          <select value={filters.estado} onChange={(e) => dispatch({ type: 'SET_FILTER', payload: { name: 'estado', value: e.target.value } })}>
            <option value="">Todos</option>
            {STATES.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Tipo
          <select value={filters.tipo} onChange={(e) => dispatch({ type: 'SET_FILTER', payload: { name: 'tipo', value: e.target.value } })}>
            <option value="">Todos</option>
            {TYPES.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <div className="actions">
          <button type="button" className="secondary" disabled={loading} onClick={loadRows}>Aplicar</button>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Apoderado</th>
              <th>Profesor</th>
              <th>Motivo</th>
              <th>Tipo</th>
              <th>Estado</th>
              <th>Fecha Propuesta</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.id}</td>
                <td>{row.apoderado_nombre || '-'}</td>
                <td>{row.profesor_nombre || '-'}</td>
                <td>{row.motivo}</td>
                <td>{row.tipo}</td>
                <td>{row.estado_display || row.estado}</td>
                <td>{row.fecha_propuesta || '-'}</td>
                <td>
                  <div className="actions-cell actions-wrap">
                    <input
                      className="small"
                      placeholder="Respuesta"
                      value={responseText[row.id] || ''}
                      onChange={(e) => dispatch({ type: 'SET_RESPONSE_TEXT', payload: { id: row.id, value: e.target.value } })}
                    />
                    <input
                      className="small"
                      type="date"
                      value={newDate[row.id] || ''}
                      onChange={(e) => dispatch({ type: 'SET_NEW_DATE', payload: { id: row.id, value: e.target.value } })}
                    />
                    <input
                      className="small"
                      type="time"
                      value={newTime[row.id] || ''}
                      onChange={(e) => dispatch({ type: 'SET_NEW_TIME', payload: { id: row.id, value: e.target.value } })}
                    />
                    <button
                      type="button"
                      className="small secondary"
                      disabled={savingId === row.id}
                      onClick={() => respond(row, 'aceptar')}
                    >
                      Aceptar
                    </button>
                    <button
                      type="button"
                      className="small secondary"
                      disabled={savingId === row.id}
                      onClick={() => respond(row, 'proponer_fecha')}
                    >
                      Reprogramar
                    </button>
                    <button
                      type="button"
                      className="small danger"
                      disabled={savingId === row.id}
                      onClick={() => respond(row, 'rechazar')}
                    >
                      Rechazar
                    </button>
                    <button
                      type="button"
                      className="small"
                      disabled={savingId === row.id}
                      onClick={() => cancelMeeting(row)}
                    >
                      Cancelar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!rows.length && !loading ? (
              <tr>
                <td colSpan={8}>Sin reuniones para los filtros seleccionados.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      {loading ? <p>Cargando…</p> : null}
    </section>
  );
}


