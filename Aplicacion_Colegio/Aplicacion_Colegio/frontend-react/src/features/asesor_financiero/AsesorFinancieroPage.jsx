import { useState } from 'react';

import { apiClient } from '../../services/apiClient';
import { useQuery } from '@tanstack/react-query';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { formatNumber } from '../../utils/formatters';

const CLP_FORMATTER = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0,
});

function resolveError(err, fallback) {
  return err?.payload?.error || err?.payload?.detail || fallback;
}

function formatCurrency(value) {
  const numeric = Number(value || 0);
  return CLP_FORMATTER.format(numeric);
}



export default function AsesorFinancieroPage() {
  const [anio, setAnio] = useState(() => new Date().getFullYear());
  const [mes, setMes] = useState('');

  const dashboardUrl = `/api/v1/finanzas/dashboard/?anio=${anio}${mes ? `&mes=${mes}` : ''}`;
  const { data: dashboardData, isLoading: dashboardLoading, error: dashboardErrorObj } = useQuery({
    queryKey: ['finanzas-dashboard', anio, mes],
    queryFn: () => apiClient.get(dashboardUrl)
  });
  const { data: morososData, isLoading: morososLoading, error: morososErrorObj } = useQuery({
    queryKey: ['finanzas-morosos'],
    queryFn: () => apiClient.get('/api/v1/finanzas/morosos/')
  });
  const dashboardError = dashboardErrorObj?.message;
  const morososError = morososErrorObj?.message;

  // Derive data inline from query results (no useEffect sync needed)
  const dashboard = dashboardData || null;
  const morosos = Array.isArray(morososData?.morosos) ? morososData.morosos.slice(0, 8) : [];

  const loading = dashboardLoading || morososLoading;
  const error = dashboardError || morososError;

  const resumen = dashboard?.resumen || {};
  const morosidad = dashboard?.morosidad || {};
  const cuotasPorEstado = Array.isArray(dashboard?.cuotas_por_estado) ? dashboard.cuotas_por_estado : [];
  const becas = dashboard?.becas || {};
  const pagosRecientes = Array.isArray(dashboard?.pagos_recientes) ? dashboard.pagos_recientes : [];
  const resumenCards = [
    {
      title: 'Emitido',
      value: resumen.total_emitido,
      subtitle: 'Monto total calculado en el periodo',
    },
    {
      title: 'Pagado',
      value: resumen.total_pagado,
      subtitle: 'Pagos confirmados en el corte actual',
    },
    {
      title: 'Pendiente',
      value: resumen.total_pendiente,
      subtitle: 'Saldo aún por recaudar',
    },
    {
      title: 'Cobranza',
      value: resumen.tasa_cobranza ?? 0,
      subtitle: 'Porcentaje de recuperación',
    },
  ];

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="asesor-financiero-title">Asesor Financiero</h2>
          <p>Dashboard financiero consolidado y reporte de morosos.</p>
        </div>
        <div className="actions">
          <label>
            Anio
            <input
              type="number"
              min="2020"
              max="2100"
              value={anio}
              onChange={(e) => setAnio(Number(e.target.value) || 2024)}
            />
          </label>
          <label>
            Mes
            <select value={mes} onChange={(e) => setMes(e.target.value)}>
              <option value="">Todos</option>
              {Array.from({ length: 12 }).map((_, idx) => {
                const month = String(idx + 1);
                return (
                  <option key={month} value={month}>
                    {month}
                  </option>
                );
              })}
            </select>
          </label>
        </div>
      </header>

      {error ? <div className="error-box" data-testid="asesor-financiero-error" role="alert" aria-live="assertive">{error}</div> : null}

      <div>
        <div className="summary-grid" data-testid="asesor-financiero-summary">
          {loading
            ? Array.from({ length: 4 }).map((_, index) => (
                <SummarySkeleton key={index} />
              ))
            : resumenCards.map((item) => (
                <article key={item.title} className="summary-tile">
                  <small>{item.title}</small>
                  <strong>{item.title === 'Cobranza' ? `${formatNumber(item.value)}%` : formatCurrency(item.value)}</strong>
                  <span>{item.subtitle}</span>
                </article>
              ))}
        </div>

        <div className="grid-2" style={{ marginTop: '1.25rem' }}>
          <article className="card section-card">
            <h3>Resumen Financiero</h3>
            {loading ? (
              <TableLoadingState />
            ) : (
              <>
                <p>Total emitido: {formatCurrency(resumen.total_emitido)}</p>
                <p>Total pagado: {formatCurrency(resumen.total_pagado)}</p>
                <p>Total pendiente: {formatCurrency(resumen.total_pendiente)}</p>
                <p>Tasa de cobranza: {resumen.tasa_cobranza ?? 0}%</p>
              </>
            )}
          </article>

          <article className="card section-card">
            <h3>Morosidad</h3>
            {loading ? (
              <TableLoadingState />
            ) : (
              <>
                <p>Familias morosas: {morosidad.familias_morosas ?? 0}</p>
                <p>Monto vencido: {formatCurrency(morosidad.monto_vencido)}</p>
                <p>Total de casos listados: {morosos.length}</p>
              </>
            )}
          </article>

          <article className="card section-card">
            <h3>Becas</h3>
            {loading ? (
              <TableLoadingState />
            ) : (
              <>
                <p>Vigentes: {becas.vigentes ?? 0}</p>
                {Array.isArray(becas.por_tipo) && becas.por_tipo.length ? (
                  <ul>
                    {becas.por_tipo.map((item) => (
                      <li key={item.tipo}>
                        {item.tipo}: {item.total}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Sin becas vigentes.</p>
                )}
              </>
            )}
          </article>

          <article className="card section-card">
            <h3>Cuotas por Estado</h3>
            {loading ? (
              <TableLoadingState />
            ) : cuotasPorEstado.length ? (
              <ul>
                {cuotasPorEstado.map((item) => (
                  <li key={item.estado}>
                    {item.estado}: {item.cantidad} ({formatCurrency(item.monto)})
                  </li>
                ))}
              </ul>
            ) : (
              <p>Sin datos del periodo.</p>
            )}
          </article>

          <article className="card section-card">
            <h3>Pagos recientes</h3>
            {loading ? (
              <TableLoadingState />
            ) : pagosRecientes.length === 0 ? (
              <p>Sin pagos para mostrar.</p>
            ) : (
              <ul>
                {pagosRecientes.map((item) => (
                  <li key={item.id}>
                    {item.estudiante || 'Sin estudiante'} - {formatCurrency(item.monto)} ({item.estado})
                  </li>
                ))}
              </ul>
            )}
          </article>

          <article className="card section-card">
            <h3>Top Morosos</h3>
            {loading ? (
              <TableLoadingState />
            ) : morosos.length === 0 ? (
              <p>Sin morosos al corte.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Estudiante</th>
                      <th>Cuotas vencidas</th>
                      <th>Monto adeudado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {morosos.map((item) => (
                      <tr key={item.estudiante_id}>
                        <td>{item.nombre}</td>
                        <td>{item.cuotas_vencidas}</td>
                        <td>{formatCurrency(item.monto_total_adeudado)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        </div>
      </div>
    </section>
  );
}

