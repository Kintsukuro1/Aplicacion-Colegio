import { useEffect, useMemo, useState } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';

import { apiClient } from '../../services/apiClient';
import { useFetch } from '../../hooks';
import { usePermissions } from '../../hooks/usePermissions';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { formatNumber } from '../../utils/formatters';



export default function ActiveSessionsPage() {
  const me = useAuthStore((state) => state.user);
  const [message, setMessage] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const { canAny } = usePermissions(me);
  const canView = canAny(['AUDIT_VIEW', 'SYSTEM_ADMIN']);

  const { data: sessionsData, loading: loadingSessions, error: errorSessions, refetch: refetchSessions } = useFetch('/api/v1/seguridad/sesiones-activas/');
  const { data: dashboardData, loading: loadingDashboard, error: errorDashboard, refetch: refetchDashboard } = useFetch('/api/v1/seguridad/dashboard/');

  const loading = loadingSessions || loadingDashboard;
  const error = errorSessions || errorDashboard;

  // Derive rows and dashboard inline from query data (no useEffect sync needed)
  const rows = Array.isArray(sessionsData?.sesiones) ? sessionsData.sesiones : [];
  const dashboard = dashboardData || null;

  const summaryCards = useMemo(
    () => [
      {
        title: 'Sesiones activas',
        value: rows.length,
        subtitle: rows.length > 0 ? 'Usuarios con sesion vigente' : 'Sin sesiones visibles',
      },
      {
        title: 'IPs bloqueadas',
        value: dashboard?.ips_bloqueadas ?? 0,
        subtitle: 'Direcciones con restriccion activa',
      },
      {
        title: 'Fallos 24h',
        value: dashboard?.intentos_fallidos_24h ?? 0,
        subtitle: 'Intentos fallidos recientes',
      },
      {
        title: 'Accesos sensibles',
        value: dashboard?.accesos_datos_sensibles_24h ?? 0,
        subtitle: 'Eventos de acceso auditados',
      },
    ],
    [dashboard, rows.length]
  );

  async function loadRows() {
    await Promise.all([refetchSessions(), refetchDashboard()]);
  }

  async function revokeSession(row) {
    if (!window.confirm(`Revocar sesion #${row.id} de ${row.user_email}?`)) {
      return;
    }
    setErrorMsg('');
    try {
      await apiClient.post(`/api/v1/seguridad/sesiones/${row.id}/revocar/`, {});
      setMessage(`Sesion #${row.id} revocada correctamente.`);
      await loadRows();
    } catch (err) {
      setErrorMsg(err.payload?.detail || 'No se pudo revocar la sesion.');
    }
  }

  async function unblockIp(ip) {
    if (!window.confirm(`Desbloquear IP ${ip}?`)) {
      return;
    }
    setErrorMsg('');
    setMessage('');
    try {
      const payload = await apiClient.post('/api/v1/seguridad/desbloquear-ip/', { ip });
      setMessage(payload?.detail || `IP ${ip} desbloqueada.`);
      await loadRows();
    } catch (err) {
      setErrorMsg(err.payload?.detail || 'No se pudo desbloquear la IP.');
    }
  }

  useEffect(() => {
    if (!canView) return;
    loadRows();
  }, [canView]);

  if (!canView) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="active-sessions-title">Seguridad: Sesiones Activas</h2>
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
          <h2>Seguridad: Sesiones Activas</h2>
          <p>Monitoreo y revocación remota por usuario y por IP bloqueada.</p>
        </div>
      </header>

      {error || errorMsg ? <div className="error-box" data-testid="active-sessions-error" role="alert" aria-live="assertive">{error || errorMsg}</div> : null}
      {message ? <div className="info-box">{message}</div> : null}

      <div className="summary-grid" data-testid="active-sessions-summary">
        {loading
          ? Array.from({ length: 5 }).map((_, index) => (
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

      <div className="summary-grid section-card">
        {loading ? (
          Array.from({ length: 5 }).map((_, index) => <SummarySkeleton key={`dash-${index}`} />)
        ) : dashboard && !error ? (
          <>
            <div className="summary-tile">
              <small>Colegio</small>
              <strong>{dashboard.colegio || '-'}</strong>
            </div>
            <div className="summary-tile">
              <small>Intentos fallidos 24h</small>
              <strong>{dashboard.intentos_fallidos_24h ?? 0}</strong>
            </div>
            <div className="summary-tile">
              <small>IPs bloqueadas</small>
              <strong>{dashboard.ips_bloqueadas ?? 0}</strong>
            </div>
            <div className="summary-tile">
              <small>Sesiones activas</small>
              <strong>{dashboard.sesiones_activas ?? 0}</strong>
            </div>
            <div className="summary-tile">
              <small>Accesos datos sensibles 24h</small>
              <strong>{dashboard.accesos_datos_sensibles_24h ?? 0}</strong>
            </div>
          </>
        ) : null}
      </div>

      <article className="card section-card">
        <h3>IPs bloqueadas</h3>
        {loading ? (
          <TableLoadingState />
        ) : !error && dashboard && Array.isArray(dashboard.ips_bloqueadas_lista) ? (
          dashboard.ips_bloqueadas_lista.length ? (
            <ul>
              {dashboard.ips_bloqueadas_lista.map((ip) => (
                <li key={ip} className="blocked-ip-item">
                  <span>{ip}</span>
                  <button type="button" className="small secondary" onClick={() => unblockIp(ip)}>
                    Desbloquear
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p>Sin IPs bloqueadas.</p>
          )
        ) : null}
      </article>

      <article className="card section-card">
        <div className="section-card-head">
          <div>
            <h3>Tabla de sesiones</h3>
            <p>Sesiones activas detectadas para el usuario y el colegio actual.</p>
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
                  <th>IP</th>
                  <th>Dispositivo</th>
                  <th>Ultima Actividad</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.user_email}</td>
                    <td>{row.user_rol || '-'}</td>
                    <td>{row.colegio_rbd || '-'}</td>
                    <td>{row.ip}</td>
                    <td>{row.dispositivo}</td>
                    <td>{row.ultima_actividad}</td>
                    <td className="actions-cell">
                      <button type="button" className="small danger" onClick={() => revokeSession(row)}>
                        Revocar
                      </button>
                    </td>
                  </tr>
                ))}
                {!rows.length ? (
                  <tr>
                    <td colSpan={8}>No hay sesiones activas para mostrar.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </section>
  );
}


