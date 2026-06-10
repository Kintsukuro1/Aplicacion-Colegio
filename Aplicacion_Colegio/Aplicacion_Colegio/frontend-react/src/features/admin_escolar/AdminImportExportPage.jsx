import { useMemo, useReducer, useRef } from 'react';
import { useAuthStore } from '../../stores/useAuthStore';

import { apiClient } from '../../services/apiClient';
import { useFetch } from '../../hooks';
import { usePermissions } from '../../hooks/usePermissions';
import { getAccessToken } from '../../stores/authStore';
import { SummarySkeleton } from '../../components/feedback/TableLoadingState';
import { formatNumber } from '../../utils/formatters';
import { useToast } from '../../components/feedback/Toast';

import { ImportSection } from './ImportSection';
import { ExportSection } from './ExportSection';

function getFilenameFromDisposition(disposition, fallbackName) {
  if (!disposition) {
    return fallbackName;
  }

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  if (plainMatch?.[1]) {
    return plainMatch[1];
  }

  return fallbackName;
}

async function parseErrorPayload(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    const payload = await response.json();
    return payload?.detail || JSON.stringify(payload);
  }
  const text = await response.text();
  return text || response.statusText;
}

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
    const detail = await parseErrorPayload(response);
    throw new Error(detail || 'No se pudo descargar el archivo.');
  }

  const disposition = response.headers.get('content-disposition');
  const fileName = getFilenameFromDisposition(disposition, fallbackName);
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

const initialState = {
  tipo: 'estudiantes',
  importing: false,
  importResult: null,
  claseId: '',
  mes: '',
  anio: '',
  exporting: false,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_FIELD':
      return { ...state, [action.payload.name]: action.payload.value };
    case 'START_IMPORT':
      return { ...state, importing: true, importResult: null };
    case 'FINISH_IMPORT':
      return { ...state, importing: false, importResult: action.payload.result };
    case 'IMPORT_ERROR':
      return { ...state, importing: false };
    case 'START_EXPORT':
      return { ...state, exporting: true };
    case 'FINISH_EXPORT':
      return { ...state, exporting: false };
    default:
      return state;
  }
}

export default function AdminImportExportPage() {
  const me = useAuthStore((state) => state.user);
  const toast = useToast();
  const permissions = usePermissions(me);
  const archivoRef = useRef(null);

  const [state, dispatch] = useReducer(reducer, initialState);
  const { tipo, importing, importResult, claseId, mes, anio, exporting } = state;

  const canAccess = useMemo(() => permissions.canAny(['SYSTEM_ADMIN', 'SYSTEM_CONFIGURE']), [permissions]);
  const canMutateImportExport = permissions.isSystemAdmin;

  const { data: dashboardResp, loading: dashboardLoading, error: dashboardError, refetch: refetchDashboard } = useFetch(
    '/api/v1/importacion/dashboard/',
    { skip: !canAccess }
  );

  const dashboard = dashboardResp || null;

  const { data: clasesResp, error: clasesErrorHook } = useFetch('/api/v1/profesor/clases/?page=1', { skip: !canAccess });
  const clases = (() => {
    if (clasesErrorHook) return [];
    return Array.isArray(clasesResp?.results) ? clasesResp.results : [];
  })();

  async function onDownloadTemplate() {
    try {
      dispatch({ type: 'START_EXPORT' });
      await downloadWithAuth(`/api/v1/importacion/plantilla/${tipo}/`, `plantilla_${tipo}.csv`);
      toast.success('Plantilla descargada correctamente.');
    } catch (err) {
      toast.error(err.message || 'No se pudo descargar la plantilla.');
    } finally {
      dispatch({ type: 'FINISH_EXPORT' });
    }
  }

  async function onImportSubmit(event) {
    event.preventDefault();

    if (!archivoRef.current) {
      toast.error('Debes seleccionar un archivo CSV o XLSX.');
      return;
    }

    try {
      dispatch({ type: 'START_IMPORT' });

      const formData = new FormData();
      formData.append('tipo', tipo);
      formData.append('archivo', archivoRef.current);

      const access = getAccessToken();
      const headers = {};
      if (access) {
        headers.Authorization = `Bearer ${access}`;
      }

      const response = await fetch(`${apiClient.baseUrl}/api/v1/importacion/importar/`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const detail = await parseErrorPayload(response);
        throw new Error(detail || 'No se pudo importar el archivo.');
      }

      const payload = await response.json();
      dispatch({ type: 'FINISH_IMPORT', payload: { result: payload } });
      archivoRef.current = null;
      toast.success('Importacion completada.');

      await refetchDashboard();
    } catch (err) {
      dispatch({ type: 'IMPORT_ERROR' });
      toast.error(err.message || 'No se pudo importar el archivo.');
    }
  }

  async function onExport(endpoint, queryString, fallbackName) {
    try {
      dispatch({ type: 'START_EXPORT' });
      await downloadWithAuth(`/api/v1/exportacion/${endpoint}/${queryString}`, fallbackName);
      toast.success('Exportacion generada correctamente.');
    } catch (err) {
      toast.error(err.message || 'No se pudo exportar archivo.');
    } finally {
      dispatch({ type: 'FINISH_EXPORT' });
    }
  }

  async function onExportReporteAcademico() {
    if (!claseId.trim()) {
      toast.error('Debes indicar un clase_id para exportar reporte academico.');
      return;
    }
    await onExport('reporte-academico', `?clase_id=${encodeURIComponent(claseId.trim())}`, 'reporte_academico.csv');
  }

  async function onExportAsistencia() {
    if (!claseId.trim()) {
      toast.error('Debes indicar un clase_id para exportar asistencia.');
      return;
    }

    const params = new URLSearchParams();
    params.set('clase_id', claseId.trim());
    if (mes.trim()) {
      params.set('mes', mes.trim());
    }
    if (anio.trim()) {
      params.set('anio', anio.trim());
    }

    await onExport('asistencia', `?${params.toString()}`, 'reporte_asistencia.csv');
  }

  if (!canAccess) {
    return (
      <section>
        <header className="page-header">
          <div>
            <h2 data-testid="admin-import-export-title">Admin Escolar: Importacion y Exportacion</h2>
            <p>No tienes permisos para acceder a este modulo.</p>
          </div>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>Admin Escolar: Importacion y Exportacion</h2>
          <p>Modulo funcional para los endpoints de carga masiva y exportacion.</p>
        </div>
      </header>

      {!canMutateImportExport ? (
        <div className="card" role="status">
          <strong>Vista de consulta</strong>
          <p>
            Tu rol puede ver el resumen del colegio, pero no ejecutar importaciones ni exportaciones masivas.
          </p>
        </div>
      ) : null}

      {dashboardError ? <div className="error-box" data-testid="admin-import-export-error" role="alert" aria-live="assertive">{dashboardError}</div> : null}

      <div className="grid-2">
        <article className="card">
          <h3>Dashboard de Datos</h3>
          <div className="stats-grid">
            {dashboardLoading
              ? Array.from({ length: 3 }).map((_, index) => (
                  <SummarySkeleton key={index} />
                ))
              : [
                  { label: 'Estudiantes', value: dashboard?.total_estudiantes ?? 0 },
                  { label: 'Profesores', value: dashboard?.total_profesores ?? 0 },
                  { label: 'Apoderados', value: dashboard?.total_apoderados ?? 0 },
                ].map((item) => (
                  <div key={item.label} className="stat-tile">
                    <small>{item.label}</small>
                    <strong>{formatNumber(item.value)}</strong>
                  </div>
                ))}
          </div>
        </article>

        {canMutateImportExport ? (
          <ImportSection
            tipo={tipo}
            importing={importing}
            exporting={exporting}
            importResult={importResult}
            onTipoChange={(val) => dispatch({ type: 'SET_FIELD', payload: { name: 'tipo', value: val } })}
            onFileChange={(e) => { archivoRef.current = e.target.files?.[0] || null; }}
            onDownloadTemplate={onDownloadTemplate}
            onImportSubmit={onImportSubmit}
          />
        ) : null}
      </div>

      {canMutateImportExport ? (
        <ExportSection
          clases={clases}
          claseId={claseId}
          mes={mes}
          anio={anio}
          importing={importing}
          exporting={exporting}
          onClaseIdChange={(val) => dispatch({ type: 'SET_FIELD', payload: { name: 'claseId', value: val } })}
          onMesChange={(val) => dispatch({ type: 'SET_FIELD', payload: { name: 'mes', value: val } })}
          onAnioChange={(val) => dispatch({ type: 'SET_FIELD', payload: { name: 'anio', value: val } })}
          onExport={onExport}
          onExportReporteAcademico={onExportReporteAcademico}
          onExportAsistencia={onExportAsistencia}
        />
      ) : (
        <article className="card section-card">
          <h3>Exportacion de Reportes</h3>
          <p>Las exportaciones masivas requieren rol de administrador del sistema.</p>
        </article>
      )}
    </section>
  );
}
