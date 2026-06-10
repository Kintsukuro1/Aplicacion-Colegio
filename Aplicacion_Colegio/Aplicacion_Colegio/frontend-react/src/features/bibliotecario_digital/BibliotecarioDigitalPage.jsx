import { useMemo, useReducer } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';

import { apiClient } from '../../services/apiClient';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { formatNumber } from '../../utils/formatters';

import { ResourceForm } from './ResourceForm';
import { PublishForm } from './PublishForm';
import { LoanForm } from './LoanForm';
import { ReturnForm } from './ReturnForm';

function resolveError(err, fallback) {
  return err?.payload?.error || err?.payload?.detail || fallback;
}

const EMPTY_RESOURCE = {
  titulo: '',
  descripcion: '',
  tipo: 'DOCUMENTO',
  url_externa: '',
  publicado: false,
  es_plan_lector: false,
};

const EMPTY_PUBLISH_FORM = { recurso_id: '' };
const EMPTY_LOAN_FORM = { recurso_id: '', usuario_id: '', dias_prestamo: 14 };
const EMPTY_RETURN_FORM = { prestamo_id: '' };

const initialState = {
  resourceForm: EMPTY_RESOURCE,
  publishForm: EMPTY_PUBLISH_FORM,
  loanForm: EMPTY_LOAN_FORM,
  returnForm: EMPTY_RETURN_FORM,
  saving: false,
  publishSaving: false,
  loanSaving: false,
  returnSaving: false,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_RESOURCE_FIELD':
      return { ...state, resourceForm: { ...state.resourceForm, [action.name]: action.value } };
    case 'SET_PUBLISH_FIELD':
      return { ...state, publishForm: { ...state.publishForm, [action.name]: action.value } };
    case 'SET_LOAN_FIELD':
      return { ...state, loanForm: { ...state.loanForm, [action.name]: action.value } };
    case 'SET_RETURN_FIELD':
      return { ...state, returnForm: { ...state.returnForm, [action.name]: action.value } };
    case 'RESET_RESOURCE_FORM':
      return { ...state, resourceForm: EMPTY_RESOURCE };
    case 'RESET_PUBLISH_FORM':
      return { ...state, publishForm: EMPTY_PUBLISH_FORM };
    case 'RESET_LOAN_FORM':
      return { ...state, loanForm: EMPTY_LOAN_FORM };
    case 'RESET_RETURN_FORM':
      return { ...state, returnForm: EMPTY_RETURN_FORM };
    case 'SET_SAVING':
      return { ...state, [action.field]: action.value };
    default:
      return state;
  }
}

export default function BibliotecarioDigitalPage() {
  const me = useAuthStore((state) => state.user);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [state, dispatch] = useReducer(reducer, initialState);

  const { canAny } = usePermissions(me);
  const canCreate = canAny(['LIBRARY_CREATE', 'SYSTEM_ADMIN']);
  const canEdit = canAny(['LIBRARY_EDIT', 'SYSTEM_ADMIN']);
  const canManageLoans = canAny(['LIBRARY_MANAGE_LOANS', 'SYSTEM_ADMIN']);

  const { data: resourcesData, isLoading: loadingResources, error: errorResourcesObj } = useQuery({
    queryKey: ['bibliotecario-recursos'],
    queryFn: () => apiClient.get('/api/bibliotecario/recursos/')
  });
  const { data: usersData, isLoading: loadingUsers } = useQuery({
    queryKey: ['bibliotecario-usuarios'],
    queryFn: () => apiClient.get('/api/bibliotecario/usuarios/')
  });
  const { data: loansData, isLoading: loadingLoans } = useQuery({
    queryKey: ['bibliotecario-prestamos'],
    queryFn: () => apiClient.get('/api/bibliotecario/prestamos/')
  });

  const loading = loadingResources || loadingUsers || loadingLoans;
  const error = errorResourcesObj?.message;

  const resources = Array.isArray(resourcesData?.recursos) ? resourcesData.recursos : [];
  const users = Array.isArray(usersData?.usuarios) ? usersData.usuarios : [];
  const loans = Array.isArray(loansData?.prestamos) ? loansData.prestamos : [];
  
  const summaryCards = useMemo(() => {
    const publishedCount = resources.filter((item) => item.publicado).length;
    const loanCount = loans.length;

    return [
      {
        title: 'Recursos',
        value: resources.length,
        subtitle: resources.length > 0 ? 'Materiales cargados en el catálogo' : 'Sin recursos cargados',
      },
      {
        title: 'Publicados',
        value: publishedCount,
        subtitle: 'Recursos visibles para la comunidad',
      },
      {
        title: 'Usuarios',
        value: users.length,
        subtitle: 'Disponibles para préstamos y búsquedas',
      },
      {
        title: 'Préstamos activos',
        value: loanCount,
        subtitle: loanCount > 0 ? 'Circulación actual en curso' : 'No hay préstamos activos',
      },
    ];
  }, [loans.length, resources, users.length]);

  async function onSubmit(event) {
    event.preventDefault();
    if (!canCreate) {
      toast.error('No tienes permisos para crear recursos.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'saving', value: true });
    try {
      const payload = await apiClient.post('/api/bibliotecario/recursos/crear/', state.resourceForm);
      toast.success(payload?.message || 'Recurso creado.');
      dispatch({ type: 'RESET_RESOURCE_FORM' });
      await queryClient.invalidateQueries({ queryKey: ['bibliotecario-recursos'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo crear el recurso.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'saving', value: false });
    }
  }

  async function onTogglePublish(event) {
    event.preventDefault();
    if (!canEdit) {
      toast.error('No tienes permisos para publicar/despublicar recursos.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'publishSaving', value: true });
    try {
      const payload = await apiClient.post(`/api/bibliotecario/recursos/${state.publishForm.recurso_id}/publicar/`, {});
      toast.success(payload?.message || 'Publicacion actualizada.');
      dispatch({ type: 'RESET_PUBLISH_FORM' });
      await queryClient.invalidateQueries({ queryKey: ['bibliotecario-recursos'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo cambiar publicacion.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'publishSaving', value: false });
    }
  }

  async function onCreateLoan(event) {
    event.preventDefault();
    if (!canManageLoans) {
      toast.error('No tienes permisos para gestionar prestamos.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'loanSaving', value: true });
    try {
      const payload = await apiClient.post('/api/bibliotecario/prestamos/crear/', {
        recurso_id: Number(state.loanForm.recurso_id),
        usuario_id: Number(state.loanForm.usuario_id),
        dias_prestamo: Number(state.loanForm.dias_prestamo),
      });
      toast.success(payload?.message || 'Prestamo registrado.');
      if (payload?.id) {
        dispatch({ type: 'SET_RETURN_FIELD', name: 'prestamo_id', value: String(payload.id) });
      }
      await queryClient.invalidateQueries({ queryKey: ['bibliotecario-prestamos'] });
      dispatch({ type: 'RESET_LOAN_FORM' });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo crear el prestamo.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'loanSaving', value: false });
    }
  }

  async function onReturnLoan(event) {
    event.preventDefault();
    if (!canManageLoans) {
      toast.error('No tienes permisos para registrar devoluciones.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'returnSaving', value: true });
    try {
      const payload = await apiClient.post(`/api/bibliotecario/prestamos/${state.returnForm.prestamo_id}/devolver/`, {});
      toast.success(payload?.message || 'Devolucion registrada.');
      dispatch({ type: 'RESET_RETURN_FORM' });
      await queryClient.invalidateQueries({ queryKey: ['bibliotecario-prestamos'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo registrar devolucion.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'returnSaving', value: false });
    }
  }

  async function quickReturnLoan(loanId) {
    if (!canManageLoans) {
      toast.error('No tienes permisos para registrar devoluciones.');
      return;
    }

    dispatch({ type: 'SET_SAVING', field: 'returnSaving', value: true });
    try {
      const payload = await apiClient.post(`/api/bibliotecario/prestamos/${loanId}/devolver/`, {});
      toast.success(payload?.message || 'Devolucion registrada.');
      await queryClient.invalidateQueries({ queryKey: ['bibliotecario-prestamos'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo registrar devolucion.'));
    } finally {
      dispatch({ type: 'SET_SAVING', field: 'returnSaving', value: false });
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="bibliotecario-digital-title">Bibliotecario Digital</h2>
          <p>Catálogo de recursos, publicaciones y préstamos con permisos por acción.</p>
        </div>
      </header>

      {error ? <div className="error-box" data-testid="bibliotecario-digital-error" role="alert" aria-live="assertive">{error}</div> : null}

      <div className="summary-grid" data-testid="bibliotecario-digital-summary">
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

      <div className="grid-2">
        <article className="card section-card">
          <h3>Recursos ({resources.length})</h3>
          {loading ? (
            <TableLoadingState />
          ) : resources.length === 0 ? (
            <p>Sin recursos.</p>
          ) : (
            <ul>
              {resources.slice(0, 12).map((item) => (
                <li key={item.id || item.id_recurso}>
                  {item.titulo || 'Sin titulo'} - {item.tipo || 'N/A'}
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="card section-card">
          <h3>Usuarios para prestamo ({users.length})</h3>
          {loading ? (
            <TableLoadingState />
          ) : users.length === 0 ? (
            <p>Sin usuarios visibles o sin permisos.</p>
          ) : (
            <ul>
              {users.slice(0, 12).map((item) => (
                <li key={item.id}>{item.nombre || item.full_name || `Usuario #${item.id}`}</li>
              ))}
            </ul>
          )}
        </article>
      </div>

      <ResourceForm
        form={state.resourceForm}
        saving={state.saving}
        canCreate={canCreate}
        onChange={(name, value) => dispatch({ type: 'SET_RESOURCE_FIELD', name, value })}
        onSubmit={onSubmit}
      />

      <div className="grid-2">
        <PublishForm
          resources={resources}
          form={state.publishForm}
          saving={state.publishSaving}
          canEdit={canEdit}
          onChange={(name, value) => dispatch({ type: 'SET_PUBLISH_FIELD', name, value })}
          onSubmit={onTogglePublish}
        />

        <LoanForm
          resources={resources}
          users={users}
          form={state.loanForm}
          saving={state.loanSaving}
          canManageLoans={canManageLoans}
          onChange={(name, value) => dispatch({ type: 'SET_LOAN_FIELD', name, value })}
          onSubmit={onCreateLoan}
        />
      </div>

      <ReturnForm
        form={state.returnForm}
        saving={state.returnSaving}
        canManageLoans={canManageLoans}
        onChange={(name, value) => dispatch({ type: 'SET_RETURN_FIELD', name, value })}
        onSubmit={onReturnLoan}
      />

      <article className="card section-card">
        <div className="section-card-head">
          <div>
            <h3>Préstamos activos ({loans.length})</h3>
            <p>Control de circulación y devoluciones desde el mismo panel.</p>
          </div>
        </div>

        {loading ? (
          <TableLoadingState />
        ) : loans.length === 0 ? (
          <p>Sin prestamos activos.</p>
        ) : (
          <ul>
            {loans.slice(0, 20).map((item) => (
              <li key={item.id}>
                <strong>#{item.id}</strong> {item.recurso} - {item.usuario}
                <div>
                  <button type="button" disabled={!canManageLoans || state.returnSaving} onClick={() => quickReturnLoan(item.id)}>
                    Devolver ahora
                  </button>
                  <button
                    type="button"
                    disabled={!canManageLoans || state.returnSaving}
                    onClick={() => dispatch({ type: 'SET_RETURN_FIELD', name: 'prestamo_id', value: String(item.id) })}
                  >
                    Usar en formulario
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
