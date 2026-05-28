import { useMemo, useReducer } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';

import { apiClient } from '../../services/apiClient';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';

function resolveError(err, fallback) {
  return err?.payload?.error || err?.payload?.detail || fallback;
}

const initialState = {
  ticketForm: { titulo: '', descripcion: '', categoria: 'OTRO', prioridad: 'MEDIA' },
  statusForm: { ticket_id: '', estado: 'EN_PROGRESO', resolucion: '' },
  resetForm: { user_id: '', approval_request_id: '', new_password: '' },
  savingTicket: false,
  savingStatus: false,
  savingReset: false,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_TICKET_FORM':
      return { ...state, ticketForm: { ...state.ticketForm, [action.payload.name]: action.payload.value } };
    case 'RESET_TICKET_FORM':
      return { ...state, ticketForm: initialState.ticketForm };
    case 'SET_STATUS_FORM':
      return { ...state, statusForm: { ...state.statusForm, [action.payload.name]: action.payload.value } };
    case 'RESET_STATUS_FORM':
      return { ...state, statusForm: initialState.statusForm };
    case 'SET_RESET_FORM':
      return { ...state, resetForm: { ...state.resetForm, [action.payload.name]: action.payload.value } };
    case 'RESET_RESET_FORM':
      return { ...state, resetForm: initialState.resetForm };
    case 'SET_SAVING':
      return { ...state, [action.payload.key]: action.payload.value };
    default:
      return state;
  }
}

function TicketFormCard({ ticketForm, savingTicket, canCreateTicket, onTicketChange, onCreateTicket }) {
  return (
    <form className="card form-grid" onSubmit={onCreateTicket}>
      <h3>Crear ticket</h3>

      <label>
        Titulo
        <input
          value={ticketForm.titulo}
          onChange={(e) => onTicketChange('titulo', e.target.value)}
          disabled={!canCreateTicket || savingTicket}
          required
        />
      </label>

      <label>
        Descripcion
        <textarea
          value={ticketForm.descripcion}
          onChange={(e) => onTicketChange('descripcion', e.target.value)}
          disabled={!canCreateTicket || savingTicket}
          required
        />
      </label>

      <label>
        Categoria
        <select
          value={ticketForm.categoria}
          onChange={(e) => onTicketChange('categoria', e.target.value)}
          disabled={!canCreateTicket || savingTicket}
        >
          <option value="ACCESO">Acceso</option>
          <option value="PLATAFORMA">Plataforma</option>
          <option value="CONTRASEÑA">Contrasena</option>
          <option value="OTRO">Otro</option>
        </select>
      </label>

      <label>
        Prioridad
        <select
          value={ticketForm.prioridad}
          onChange={(e) => onTicketChange('prioridad', e.target.value)}
          disabled={!canCreateTicket || savingTicket}
        >
          <option value="BAJA">Baja</option>
          <option value="MEDIA">Media</option>
          <option value="ALTA">Alta</option>
          <option value="URGENTE">Urgente</option>
        </select>
      </label>

      <div>
        <button type="submit" disabled={!canCreateTicket || savingTicket || !ticketForm.titulo || !ticketForm.descripcion}>
          {savingTicket ? 'Guardando...' : 'Crear ticket'}
        </button>
      </div>
    </form>
  );
}

function StatusFormCard({ statusForm, savingStatus, canResolveTicket, onStatusChange, onUpdateStatus }) {
  return (
    <form className="card form-grid" onSubmit={onUpdateStatus}>
      <h3>Actualizar ticket</h3>

      <label>
        Ticket ID
        <input
          type="number"
          min="1"
          value={statusForm.ticket_id}
          onChange={(e) => onStatusChange('ticket_id', e.target.value)}
          disabled={!canResolveTicket || savingStatus}
          required
        />
      </label>

      <label>
        Estado
        <select
          value={statusForm.estado}
          onChange={(e) => onStatusChange('estado', e.target.value)}
          disabled={!canResolveTicket || savingStatus}
        >
          <option value="ABIERTO">Abierto</option>
          <option value="EN_PROGRESO">En progreso</option>
          <option value="RESUELTO">Resuelto</option>
          <option value="CERRADO">Cerrado</option>
        </select>
      </label>

      <label>
        Resolucion
        <textarea
          value={statusForm.resolucion}
          onChange={(e) => onStatusChange('resolucion', e.target.value)}
          disabled={!canResolveTicket || savingStatus}
        />
      </label>

      <div>
        <button type="submit" disabled={!canResolveTicket || savingStatus || !statusForm.ticket_id}>
          {savingStatus ? 'Guardando...' : 'Actualizar estado'}
        </button>
      </div>
    </form>
  );
}

function ResetFormCard({ resetForm, savingReset, canResetPassword, onResetChange, onResetPassword }) {
  return (
    <form className="card form-grid" onSubmit={onResetPassword}>
      <h3>Reset de contrasena</h3>
      <p>
        Fase 1: envia solo usuario para crear solicitud. Fase 2: envia `approval_request_id` y `new_password` para ejecutar.
      </p>

      <label>
        Usuario ID
        <input
          type="number"
          min="1"
          value={resetForm.user_id}
          onChange={(e) => onResetChange('user_id', e.target.value)}
          disabled={!canResetPassword || savingReset}
          required
        />
      </label>

      <label>
        Approval Request ID (fase 2)
        <input
          type="number"
          min="1"
          value={resetForm.approval_request_id}
          onChange={(e) => onResetChange('approval_request_id', e.target.value)}
          disabled={!canResetPassword || savingReset}
        />
      </label>

      <label>
        Nueva contrasena (fase 2)
        <input
          type="password"
          value={resetForm.new_password}
          onChange={(e) => onResetChange('new_password', e.target.value)}
          disabled={!canResetPassword || savingReset}
        />
      </label>

      <div>
        <button type="submit" disabled={!canResetPassword || savingReset || !resetForm.user_id}>
          {savingReset ? 'Procesando...' : 'Ejecutar flujo reset'}
        </button>
      </div>
    </form>
  );
}

export default function SoporteTecnicoPage() {
  const me = useAuthStore((state) => state.user);
  const { canAny, isSystemAdmin } = usePermissions(me);
  const toast = useToast();

  const [state, dispatch] = useReducer(reducer, initialState);
  const { ticketForm, statusForm, resetForm, savingTicket, savingStatus, savingReset } = state;

  const canCreateTicket = isSystemAdmin || canAny(['SUPPORT_CREATE_TICKET']);
  const canResolveTicket = isSystemAdmin || canAny(['SUPPORT_RESOLVE_TICKET']);
  const canResetPassword = isSystemAdmin || canAny(['SUPPORT_RESET_PASSWORD', 'SUPPORT_RESOLVE_TICKET']);

  const summaryCards = useMemo(() => {
    return [
      {
        title: 'Crear tickets',
        value: canCreateTicket ? 'Habilitado' : 'Bloqueado',
        subtitle: canCreateTicket ? 'Puedes abrir nuevas incidencias' : 'Solo lectura para nuevos tickets',
      },
      {
        title: 'Resolver tickets',
        value: canResolveTicket ? 'Habilitado' : 'Bloqueado',
        subtitle: canResolveTicket ? 'Puedes actualizar estados' : 'No puedes cambiar estados',
      },
      {
        title: 'Reset de contraseña',
        value: canResetPassword ? 'Habilitado' : 'Bloqueado',
        subtitle: canResetPassword ? 'Puedes iniciar el flujo de segundo aprobador' : 'No puedes ejecutar resets',
      },
    ];
  }, [canCreateTicket, canResolveTicket, canResetPassword]);

  async function onCreateTicket(event) {
    event.preventDefault();
    if (!canCreateTicket) {
      toast.error('No tienes permisos para crear tickets.');
      return;
    }

    dispatch({ type: 'SET_SAVING', payload: { key: 'savingTicket', value: true } });
    try {
      const payload = await apiClient.post('/api/soporte/tickets/crear/', ticketForm);
      toast.success(payload?.message || 'Ticket creado correctamente.');
      dispatch({ type: 'RESET_TICKET_FORM' });
      if (payload?.id) {
        dispatch({ type: 'SET_STATUS_FORM', payload: { name: 'ticket_id', value: String(payload.id) } });
      }
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo crear el ticket.'));
    } finally {
      dispatch({ type: 'SET_SAVING', payload: { key: 'savingTicket', value: false } });
    }
  }

  async function onUpdateStatus(event) {
    event.preventDefault();
    if (!canResolveTicket) {
      toast.error('No tienes permisos para resolver tickets.');
      return;
    }

    dispatch({ type: 'SET_SAVING', payload: { key: 'savingStatus', value: true } });
    try {
      const payload = await apiClient.post(`/api/soporte/tickets/${statusForm.ticket_id}/estado/`, {
        estado: statusForm.estado,
        resolucion: statusForm.resolucion,
      });
      toast.success(payload?.message || 'Estado de ticket actualizado.');
      dispatch({ type: 'RESET_STATUS_FORM' });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo actualizar el ticket.'));
    } finally {
      dispatch({ type: 'SET_SAVING', payload: { key: 'savingStatus', value: false } });
    }
  }

  async function onResetPassword(event) {
    event.preventDefault();
    if (!canResetPassword) {
      toast.error('No tienes permisos para restablecer contrasenas.');
      return;
    }

    dispatch({ type: 'SET_SAVING', payload: { key: 'savingReset', value: true } });
    try {
      const payload = await apiClient.post(`/api/soporte/usuarios/${resetForm.user_id}/reset_password/`, {
        approval_request_id: resetForm.approval_request_id ? Number(resetForm.approval_request_id) : undefined,
        new_password: resetForm.new_password || undefined,
      });

      if (payload?.requires_approval && payload?.request_id) {
        toast.info(
          `Solicitud registrada (request_id ${payload.request_id}). Usa ese ID y la nueva contrasena para ejecutar el reset con segundo aprobador.`
        );
        dispatch({ type: 'SET_RESET_FORM', payload: { name: 'approval_request_id', value: String(payload.request_id) } });
      } else {
        toast.success(payload?.message || 'Contrasena restablecida correctamente.');
        dispatch({ type: 'RESET_RESET_FORM' });
      }
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo ejecutar reset de contrasena.'));
    } finally {
      dispatch({ type: 'SET_SAVING', payload: { key: 'savingReset', value: false } });
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="soporte-tecnico-title">Soporte Tecnico</h2>
          <p>Flujo operativo para tickets, estados y restablecimiento de contraseñas.</p>
        </div>
      </header>

      <div className="summary-grid" data-testid="soporte-tecnico-summary">
        {summaryCards.map((item) => (
          <article key={item.title} className="summary-tile">
            <small>{item.title}</small>
            <strong>{item.value}</strong>
            <span>{item.subtitle}</span>
          </article>
        ))}
      </div>

      <div className="grid-2">
        <TicketFormCard
          ticketForm={ticketForm}
          savingTicket={savingTicket}
          canCreateTicket={canCreateTicket}
          onTicketChange={(name, value) => dispatch({ type: 'SET_TICKET_FORM', payload: { name, value } })}
          onCreateTicket={onCreateTicket}
        />
        <StatusFormCard
          statusForm={statusForm}
          savingStatus={savingStatus}
          canResolveTicket={canResolveTicket}
          onStatusChange={(name, value) => dispatch({ type: 'SET_STATUS_FORM', payload: { name, value } })}
          onUpdateStatus={onUpdateStatus}
        />
      </div>

      <ResetFormCard
        resetForm={resetForm}
        savingReset={savingReset}
        canResetPassword={canResetPassword}
        onResetChange={(name, value) => dispatch({ type: 'SET_RESET_FORM', payload: { name, value } })}
        onResetPassword={onResetPassword}
      />
    </section>
  );
}
