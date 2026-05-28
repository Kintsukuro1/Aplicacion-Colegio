import { useMemo, useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';

import { apiClient } from '../../services/apiClient';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { usePermissions } from '../../hooks/usePermissions';
import { useToast } from '../../components/feedback/Toast';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';

function resolveError(err, fallback) {
  return err?.payload?.error || err?.payload?.detail || fallback;
}

function formatDisplay(value) {
  if (value === true) {
    return 'Si';
  }
  if (value === false) {
    return 'No';
  }
  return value;
}




export default function CoordinadorAcademicoPage() {
  const me = useAuthStore((state) => state.user);
  const toast = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    planificacion_id: '',
    estado: 'APROBADA',
    observaciones: '',
  });
  const [saving, setSaving] = useState(false);

  const { canAny } = usePermissions(me);
  const canApprove = canAny(['PLANNING_APPROVE', 'SYSTEM_ADMIN']);

  const { data: plansData, isLoading: loading, error: plansErrorObj } = useQuery({
    queryKey: ['coordinador-planificaciones'],
    queryFn: () => apiClient.get('/api/coordinador/planificaciones/')
  });
  const error = plansErrorObj?.message;

  // Derive plans inline from query results (no useEffect sync needed)
  const plans = Array.isArray(plansData?.planificaciones) ? plansData.planificaciones : [];

  const summaryCards = useMemo(
    () => [
      {
        title: 'Planes visibles',
        value: plans.length,
        subtitle: plans.length > 0 ? 'Pendientes en memoria local' : 'Sin planes cargados',
      },
      {
        title: 'Puede revisar',
        value: canApprove,
        subtitle: 'Habilitado por capability',
      },
      {
        title: 'Carga inicial',
        value: loading ? 'Activa' : 'Lista',
        subtitle: 'Estado del listado remoto',
      },
      {
        title: 'Siguiente lote',
        value: plans.length > 20 ? `${plans.length - 20}+` : '0',
        subtitle: 'Elementos fuera del primer corte',
      },
    ],
    [canApprove, loading, plans.length]
  );

  function onChange(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (!canApprove) {
      return;
    }

    setSaving(true);
    try {
      const payload = await apiClient.post(`/api/coordinador/planificaciones/${form.planificacion_id}/estado/`, {
        estado: form.estado,
        observaciones: form.observaciones,
      });
      toast.success(payload?.message || 'Estado de planificacion actualizado.');
      setForm({ planificacion_id: '', estado: 'APROBADA', observaciones: '' });
      await queryClient.invalidateQueries({ queryKey: ['coordinador-planificaciones'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo actualizar la planificacion.'));
    } finally {
      setSaving(false);
    }
  }

  async function quickUpdatePlan(planId, estado) {
    if (!canApprove) {
      return;
    }

    setSaving(true);
    try {
      const payload = await apiClient.post(`/api/coordinador/planificaciones/${planId}/estado/`, {
        estado,
        observaciones: '',
      });
      toast.success(payload?.message || 'Estado de planificacion actualizado.');
      await queryClient.invalidateQueries({ queryKey: ['coordinador-planificaciones'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo actualizar la planificacion.'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="coordinador-academico-title">Coordinador Academico</h2>
          <p>Aprobacion/rechazo rapido de planificaciones por ID.</p>
        </div>
      </header>

      {error ? <div className="error-box" data-testid="coordinador-academico-error" role="alert" aria-live="assertive">{error}</div> : null}

      <div className="summary-grid" data-testid="coordinador-academico-summary">
        {loading
          ? Array.from({ length: 4 }).map((_, index) => (
              <SummarySkeleton key={index} />
            ))
          : summaryCards.map((item) => (
              <article key={item.title} className="summary-tile">
                <small>{item.title}</small>
                <strong>{formatDisplay(item.value)}</strong>
                <span>{item.subtitle}</span>
              </article>
            ))}
      </div>

      <form className="card form-grid" onSubmit={onSubmit}>
        <h3>Actualizar estado planificacion</h3>

        <label>
          Planificacion ID
          <input
            type="number"
            min="1"
            value={form.planificacion_id}
            onChange={(e) => onChange('planificacion_id', e.target.value)}
            disabled={!canApprove || saving}
            required
          />
        </label>

        <label>
          Estado
          <select value={form.estado} onChange={(e) => onChange('estado', e.target.value)} disabled={!canApprove || saving}>
            <option value="APROBADA">Aprobada</option>
            <option value="RECHAZADA">Rechazada</option>
          </select>
        </label>

        <label>
          Observaciones
          <textarea
            value={form.observaciones}
            onChange={(e) => onChange('observaciones', e.target.value)}
            disabled={!canApprove || saving}
          />
        </label>

        <div>
          <button type="submit" disabled={!canApprove || saving || !form.planificacion_id}>
            {saving ? 'Guardando...' : 'Actualizar'}
          </button>
        </div>
      </form>

      <article className="card section-card">
        <h3>Planificaciones pendientes ({plans.length})</h3>
        {loading ? (
          <TableLoadingState />
        ) : plans.length === 0 ? (
          <p>Sin planificaciones pendientes.</p>
        ) : (
          <ul>
            {plans.slice(0, 20).map((item) => (
              <li key={item.id}>
                <strong>#{item.id}</strong> {item.titulo} - {item.clase}
                <div>
                  <button type="button" disabled={!canApprove || saving} onClick={() => quickUpdatePlan(item.id, 'APROBADA')}>
                    Aprobar
                  </button>
                  <button type="button" disabled={!canApprove || saving} onClick={() => quickUpdatePlan(item.id, 'RECHAZADA')}>
                    Rechazar
                  </button>
                  <button
                    type="button"
                    disabled={!canApprove || saving}
                    onClick={() => setForm((prev) => ({ ...prev, planificacion_id: String(item.id) }))}
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


