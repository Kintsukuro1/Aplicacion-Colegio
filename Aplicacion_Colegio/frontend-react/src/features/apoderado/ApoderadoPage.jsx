import { useEffect, useMemo, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../components/feedback/Toast';
import { SummarySkeleton, TableLoadingState } from '../../components/feedback/TableLoadingState';
import { getAccessToken } from '../../stores/authStore';
import { formatGrade, formatNumber, formatShortDate } from '../../utils/formatters';

function resolveError(err, fallback) {
  return err?.payload?.error || err?.payload?.detail || fallback;
}

async function parseErrorPayload(response) {
  try {
    const payload = await response.json();
    return payload?.error || payload?.detail || response.statusText;
  } catch {
    return response.statusText || 'Error inesperado';
  }
}

function resolveProfileName(profileUser) {
  if (!profileUser) return 'Perfil';
  const fullName = profileUser.nombre_completo || profileUser.full_name;
  if (fullName) return fullName;
  const parts = [profileUser.nombre, profileUser.apellido_paterno, profileUser.apellido_materno].filter(Boolean);
  return parts.length ? parts.join(' ') : profileUser.email || 'Perfil';
}

function buildPdfUrl(studentId, path) {
  if (!studentId) return '#';
  return `${apiClient.baseUrl}/pdf/${path}/${studentId}/`;
}

const APODERADO_TAB_ALIASES = {
  resumen: 'resumen',
  inicio: 'resumen',
  perfil: 'perfil',
  pupilos: 'pupilos',
  mis_pupilos: 'pupilos',
  notas: 'notas',
  calificaciones: 'notas',
  asistencia: 'asistencia',
  justificativos: 'justificativos',
  firmas: 'firmas',
  firmas_pendientes: 'firmas',
  calendario: 'calendario',
  calendario_pupilo: 'calendario',
  comunicados: 'comunicados',
  mensajes: 'mensajes',
  mis_certificados: 'certificados',
  certificados: 'certificados',
  estado_cuenta: 'estado_cuenta',
  mis_pagos: 'mis_pagos',
  admision: 'admision',
  admision_matricula: 'admision',
};

const APODERADO_PATH_TABS = {
  '/apoderado/perfil': 'perfil',
  '/apoderado/mis-pupilos': 'pupilos',
  '/apoderado/notas': 'notas',
  '/apoderado/asistencia': 'asistencia',
  '/apoderado/justificativos': 'justificativos',
  '/apoderado/firmas-pendientes': 'firmas',
  '/apoderado/calendario': 'calendario',
  '/apoderado/calendario-pupilo': 'calendario',
  '/apoderado/comunicados': 'comunicados',
  '/apoderado/mensajes': 'mensajes',
  '/apoderado/mis-certificados': 'certificados',
  '/apoderado/admision-matricula': 'admision',
  '/apoderado/estado-cuenta': 'estado_cuenta',
  '/apoderado/mis-pagos': 'mis_pagos',
};

function normalizeTab(value) {
  const key = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_');
  return APODERADO_TAB_ALIASES[key] || null;
}

function toArray(payload, keys = []) {
  if (Array.isArray(payload)) {
    return payload;
  }
  for (const key of keys) {
    if (Array.isArray(payload?.[key])) {
      return payload[key];
    }
  }
  if (Array.isArray(payload?.results)) {
    return payload.results;
  }
  return [];
}

function getPupilId(item) {
  return item?.id || item?.estudiante_id || item?.id_estudiante || item?.user_id || '';
}

function getPupilName(item) {
  return item?.nombre_completo || item?.estudiante_nombre || item?.nombre || item?.full_name || `Pupilo #${getPupilId(item)}`;
}



export default function ApoderadoPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab =
    normalizeTab(searchParams.get('tab') || searchParams.get('section') || searchParams.get('pagina')) ||
    APODERADO_PATH_TABS[location.pathname.replace(/\/$/, '')] ||
    'resumen';
  const [activeTab, setActiveTab] = useState(initialTab);
  const [selectedPupilId, setSelectedPupilId] = useState(searchParams.get('estudiante_id') || '');
  const [selectedConversationId, setSelectedConversationId] = useState('');
  const [signForm, setSignForm] = useState({
    tipo_documento: 'AUTORIZACION',
    titulo: '',
    contenido: '',
    estudiante_id: '',
  });
  const [saving, setSaving] = useState(false);
  const [confirmingComunicadoId, setConfirmingComunicadoId] = useState(null);
  const [admissionForm, setAdmissionForm] = useState({
    curso_id: '',
    ciclo_id: '',
    nombre_estudiante: '',
    apellido_paterno_estudiante: '',
    apellido_materno_estudiante: '',
    rut_estudiante: '',
    fecha_nacimiento_estudiante: '',
    genero_estudiante: 'O',
    direccion_hogar: '',
    telefono_contacto: '',
    parentesco: 'OTRO',
    certificado_nacimiento: null,
    certificado_medico: null,
  });
  const [admissionSaving, setAdmissionSaving] = useState(false);
  const [admissionResult, setAdmissionResult] = useState(null);
  const [contractForm, setContractForm] = useState({
    solicitud_id: '',
    rut_firmante: '',
  });
  const [contractSaving, setContractSaving] = useState(false);
  const [contractResult, setContractResult] = useState(null);

  const { data: justData, isLoading: justLoading, error: justErrorObj } = useQuery({
    queryKey: ['apoderado-justificativos'],
    queryFn: () => apiClient.get('/api/apoderado/justificativos/')
  });
  const { data: signData, isLoading: signLoading, error: signErrorObj } = useQuery({
    queryKey: ['apoderado-firmas'],
    queryFn: () => apiClient.get('/api/apoderado/firmas/')
  });
  const { data: pupilsData, isLoading: pupilsLoading, error: pupilsErrorObj } = useQuery({
    queryKey: ['apoderado-pupilos'],
    queryFn: () => apiClient.get('/api/v1/apoderado/mis-pupilos/')
  });
  const { data: profileData, isLoading: profileLoading, error: profileErrorObj } = useQuery({
    queryKey: ['apoderado-perfil'],
    queryFn: () => apiClient.get('/api/v1/perfil/mi-perfil/'),
    enabled: activeTab === 'perfil'
  });
  const { data: comunicadosData, isLoading: comunicadosLoading, error: comunicadosErrorObj } = useQuery({
    queryKey: ['apoderado-comunicados'],
    queryFn: () => apiClient.get('/api/v1/apoderado/comunicados/'),
    enabled: activeTab === 'comunicados'
  });
  const { data: conversationsData, isLoading: conversationsLoading, error: conversationsErrorObj } = useQuery({
    queryKey: ['apoderado-conversaciones'],
    queryFn: () => apiClient.get('/api/v1/mensajeria/conversaciones/'),
    enabled: activeTab === 'mensajes'
  });
  const { data: messagesData, isLoading: messagesLoading, error: messagesErrorObj } = useQuery({
    queryKey: ['apoderado-mensajes', selectedConversationId],
    queryFn: () => apiClient.get(`/api/v1/mensajeria/conversaciones/${selectedConversationId}/mensajes/`),
    enabled: activeTab === 'mensajes' && Boolean(selectedConversationId)
  });
  const { data: pagosData, isLoading: pagosLoading, error: pagosErrorObj } = useQuery({
    queryKey: ['apoderado-pagos-estado'],
    queryFn: () => apiClient.get('/api/v1/apoderado/pagos/estado/'),
    enabled: activeTab === 'estado_cuenta' || activeTab === 'mis_pagos'
  });

  const justError = justErrorObj?.message;
  const signError = signErrorObj?.message;
  const pupilsError = pupilsErrorObj?.message;
  const profileError = profileErrorObj?.message;
  const comunicadosError = comunicadosErrorObj?.message;
  const conversationsError = conversationsErrorObj?.message;
  const messagesError = messagesErrorObj?.message;
  const pagosError = pagosErrorObj?.message;

  // Derive data inline from query results (no useEffect sync needed)
  const justificativos = Array.isArray(justData?.justificativos) ? justData.justificativos : [];
  const pendientes = Array.isArray(signData?.pendientes) ? signData.pendientes : [];
  const firmados = Array.isArray(signData?.firmados) ? signData.firmados : [];
  const pupilos = toArray(pupilsData, ['pupilos', 'estudiantes']);
  const profile = profileData || null;
  const profileUser = profile?.user || {};
  const profilePupilos = Array.isArray(profile?.estudiantes_vinculados) ? profile.estudiantes_vinculados : [];
  const profileName = resolveProfileName(profileUser);
  const comunicados = toArray(comunicadosData, ['comunicados']);
  const conversaciones = toArray(conversationsData, ['conversaciones']);
  const mensajes = toArray(messagesData, ['mensajes']);
  const pagosResumen = pagosData?.resumen || null;
  const pagosPupilos = toArray(pagosData, ['pupilos']);
  const selectedPupil = useMemo(
    () => pupilos.find((item) => String(getPupilId(item)) === String(selectedPupilId)) || null,
    [pupilos, selectedPupilId]
  );

  useEffect(() => {
    if (!selectedPupilId && pupilos.length > 0) {
      setSelectedPupilId(String(getPupilId(pupilos[0])));
    }
  }, [pupilos, selectedPupilId]);

  useEffect(() => {
    if (activeTab !== 'mensajes') return;
    if (!selectedConversationId && conversaciones.length > 0) {
      const firstId = conversaciones[0]?.id_conversacion || conversaciones[0]?.id;
      if (firstId) {
        setSelectedConversationId(String(firstId));
      }
    }
  }, [activeTab, conversaciones, selectedConversationId]);

  useEffect(() => {
    const tabFromUrl =
      normalizeTab(searchParams.get('tab') || searchParams.get('section') || searchParams.get('pagina')) ||
      APODERADO_PATH_TABS[location.pathname.replace(/\/$/, '')];
    if (tabFromUrl && tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [activeTab, location.pathname, searchParams]);

  const detailEnabled = Boolean(selectedPupilId);
  const { data: gradesData, isLoading: gradesLoading, error: gradesErrorObj } = useQuery({
    queryKey: ['apoderado-pupilo-notas', selectedPupilId],
    queryFn: () => apiClient.get(`/api/v1/apoderado/pupilo/${selectedPupilId}/notas/`),
    enabled: detailEnabled && activeTab === 'notas'
  });
  const { data: attendanceData, isLoading: attendanceLoading, error: attendanceErrorObj } = useQuery({
    queryKey: ['apoderado-pupilo-asistencia', selectedPupilId],
    queryFn: () => apiClient.get(`/api/v1/apoderado/pupilo/${selectedPupilId}/asistencia/`),
    enabled: detailEnabled && activeTab === 'asistencia'
  });
  const { data: annotationsData, isLoading: annotationsLoading, error: annotationsErrorObj } = useQuery({
    queryKey: ['apoderado-pupilo-anotaciones', selectedPupilId],
    queryFn: () => apiClient.get(`/api/v1/apoderado/pupilo/${selectedPupilId}/anotaciones/`),
    enabled: detailEnabled && activeTab === 'calendario'
  });

  const notas = toArray(gradesData, ['notas', 'calificaciones', 'asignaturas']);
  const asistencias = toArray(attendanceData, ['asistencia', 'asistencias', 'registros']);
  const anotaciones = toArray(annotationsData, ['anotaciones']);
  const gradesError = gradesErrorObj?.message;
  const attendanceError = attendanceErrorObj?.message;
  const annotationsError = annotationsErrorObj?.message;

  const loading = justLoading || signLoading || pupilsLoading;
  const error =
    justError ||
    signError ||
    pupilsError ||
    gradesError ||
    attendanceError ||
    annotationsError ||
    profileError ||
    comunicadosError ||
    conversationsError ||
    messagesError ||
    pagosError;

  const summaryCards = [
    {
      title: 'Pupilos',
      value: pupilos.length,
      subtitle: pupilos.length > 0 ? 'Estudiantes vinculados' : 'Sin pupilos vinculados',
    },
    {
      title: 'Justificativos',
      value: justificativos.length,
      subtitle: justificativos.length > 0 ? 'Registros pendientes o revisados' : 'No hay justificativos cargados',
    },
    {
      title: 'Pendientes de firma',
      value: pendientes.length,
      subtitle: pendientes.length > 0 ? 'Documentos esperando acción' : 'No hay documentos pendientes',
    },
    {
      title: 'Firmados',
      value: firmados.length,
      subtitle: firmados.length > 0 ? 'Documentos ya autorizados' : 'Sin firmas registradas',
    },
  ];

  function onChange(name, value) {
    setSignForm((prev) => ({ ...prev, [name]: value }));
  }

  function onAdmissionChange(name, value) {
    setAdmissionForm((prev) => ({ ...prev, [name]: value }));
  }

  function onContractChange(name, value) {
    setContractForm((prev) => ({ ...prev, [name]: value }));
  }

  function onTabChange(tab) {
    setActiveTab(tab.id);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('tab', tab.query);
    if (selectedPupilId) {
      nextParams.set('estudiante_id', selectedPupilId);
    }
    setSearchParams(nextParams, { replace: true });
  }

  function onPupilChange(value) {
    setSelectedPupilId(value);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('estudiante_id', value);
    if (!nextParams.get('tab')) {
      nextParams.set('tab', activeTab);
    }
    setSearchParams(nextParams, { replace: true });
  }

  function onConversationChange(value) {
    setSelectedConversationId(value);
  }

  async function onSign(event) {
    event.preventDefault();

    setSaving(true);

    try {
      const payload = await apiClient.post('/api/apoderado/firmas/firmar/', {
        tipo_documento: signForm.tipo_documento,
        titulo: signForm.titulo,
        contenido: signForm.contenido,
        estudiante_id: signForm.estudiante_id ? Number(signForm.estudiante_id) : null,
      });
      toast.success(payload?.message || 'Documento firmado correctamente.');
      setSignForm({ tipo_documento: 'AUTORIZACION', titulo: '', contenido: '', estudiante_id: '' });
      await queryClient.invalidateQueries({ queryKey: ['apoderado-justificativos'] });
      await queryClient.invalidateQueries({ queryKey: ['apoderado-firmas'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo firmar el documento.'));
    } finally {
      setSaving(false);
    }
  }

  async function onConfirmComunicado(comunicadoId) {
    if (!comunicadoId) return;
    setConfirmingComunicadoId(comunicadoId);
    try {
      await apiClient.post(`/api/v1/comunicados/${comunicadoId}/confirmar/`, {});
      toast.success('Comunicado confirmado.');
      await queryClient.invalidateQueries({ queryKey: ['apoderado-comunicados'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo confirmar el comunicado.'));
    } finally {
      setConfirmingComunicadoId(null);
    }
  }

  async function onAdmissionSubmit(event) {
    event.preventDefault();
    setAdmissionSaving(true);
    setAdmissionResult(null);

    try {
      const formData = new FormData();
      Object.entries(admissionForm).forEach(([key, value]) => {
        if (value === null || value === undefined || value === '') return;
        formData.append(key, value);
      });

      const access = getAccessToken();
      const headers = {};
      if (access) {
        headers.Authorization = `Bearer ${access}`;
      }

      const response = await fetch(`${apiClient.baseUrl}/api/apoderado/admisiones/solicitar/`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const detail = await parseErrorPayload(response);
        throw new Error(detail || 'No se pudo enviar la solicitud de admision.');
      }

      const payload = await response.json();
      setAdmissionResult({ type: 'success', message: payload?.message || 'Solicitud enviada correctamente.' });
      setAdmissionForm({
        curso_id: '',
        ciclo_id: '',
        nombre_estudiante: '',
        apellido_paterno_estudiante: '',
        apellido_materno_estudiante: '',
        rut_estudiante: '',
        fecha_nacimiento_estudiante: '',
        genero_estudiante: 'O',
        direccion_hogar: '',
        telefono_contacto: '',
        parentesco: 'OTRO',
        certificado_nacimiento: null,
        certificado_medico: null,
      });
    } catch (err) {
      setAdmissionResult({ type: 'error', message: err.message || 'No se pudo enviar la solicitud.' });
    } finally {
      setAdmissionSaving(false);
    }
  }

  async function onContractSubmit(event) {
    event.preventDefault();
    setContractSaving(true);
    setContractResult(null);

    try {
      const payload = await apiClient.post('/api/apoderado/admisiones/firmar-contrato/', {
        solicitud_id: Number(contractForm.solicitud_id),
        rut_firmante: contractForm.rut_firmante,
      });
      setContractResult({ type: 'success', message: payload?.message || 'Contrato firmado correctamente.' });
      setContractForm({ solicitud_id: '', rut_firmante: '' });
    } catch (err) {
      setContractResult({ type: 'error', message: resolveError(err, 'No se pudo firmar el contrato.') });
    } finally {
      setContractSaving(false);
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="apoderado-title">Apoderado Panel</h2>
          <p>Seguimiento de justificativos y firma digital con estado resumido.</p>
        </div>
      </header>

      {error ? <div className="error-box" data-testid="apoderado-error" role="alert" aria-live="assertive">{error}</div> : null}

      <div className="tabs" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
        {[
          { id: 'resumen', label: 'Resumen', query: 'resumen' },
          { id: 'pupilos', label: 'Pupilos', query: 'pupilos' },
          { id: 'notas', label: 'Notas', query: 'notas' },
          { id: 'asistencia', label: 'Asistencia', query: 'asistencia' },
          { id: 'justificativos', label: 'Justificativos', query: 'justificativos' },
          { id: 'firmas', label: 'Firmas', query: 'firmas' },
          { id: 'calendario', label: 'Calendario', query: 'calendario' },
          { id: 'comunicados', label: 'Comunicados', query: 'comunicados' },
          { id: 'mensajes', label: 'Mensajes', query: 'mensajes' },
          { id: 'certificados', label: 'Certificados', query: 'certificados' },
          { id: 'admision', label: 'Admision', query: 'admision' },
          { id: 'estado_cuenta', label: 'Estado de cuenta', query: 'estado_cuenta' },
          { id: 'mis_pagos', label: 'Mis pagos', query: 'mis_pagos' },
          { id: 'perfil', label: 'Perfil', query: 'perfil' },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? 'primary' : 'secondary'}
            onClick={() => onTabChange(tab)}
            style={{ whiteSpace: 'nowrap' }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="summary-grid" data-testid="apoderado-summary">
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

      {['notas', 'asistencia', 'calendario'].includes(activeTab) ? (
        <article className="card section-card">
          <label>
            Pupilo
            <select value={selectedPupilId} onChange={(event) => onPupilChange(event.target.value)}>
              <option value="">Seleccionar</option>
              {pupilos.map((item) => (
                <option key={getPupilId(item)} value={getPupilId(item)}>
                  {getPupilName(item)}
                </option>
              ))}
            </select>
          </label>
        </article>
      ) : null}

      {activeTab === 'pupilos' ? (
        <article className="card section-card">
          <h3>Mis Pupilos</h3>
          {pupilsLoading ? (
            <TableLoadingState />
          ) : pupilos.length === 0 ? (
            <p>Sin pupilos vinculados.</p>
          ) : (
            <ul>
              {pupilos.map((item) => (
                <li key={getPupilId(item)}>
                  <strong>{getPupilName(item)}</strong>
                  {item.curso || item.curso_actual || item.curso_nombre ? <span> - {item.curso || item.curso_actual || item.curso_nombre}</span> : null}
                </li>
              ))}
            </ul>
          )}
        </article>
      ) : null}

      {activeTab === 'notas' ? (
        <article className="card section-card">
          <h3>Notas {selectedPupil ? `de ${getPupilName(selectedPupil)}` : ''}</h3>
          {gradesLoading ? (
            <TableLoadingState />
          ) : notas.length === 0 ? (
            <p>Sin notas disponibles.</p>
          ) : (
            <ul>
              {notas.slice(0, 20).map((item, index) => (
                <li key={item.id || item.id_calificacion || item.asignatura || index}>
                  <strong>{item.asignatura || item.evaluacion || item.nombre || 'Registro'}</strong>
                  <span> - {formatGrade(item.nota ?? item.promedio, '-')}</span>
                </li>
              ))}
            </ul>
          )}
        </article>
      ) : null}

      {activeTab === 'asistencia' ? (
        <article className="card section-card">
          <h3>Asistencia {selectedPupil ? `de ${getPupilName(selectedPupil)}` : ''}</h3>
          {attendanceLoading ? (
            <TableLoadingState />
          ) : asistencias.length === 0 ? (
            <p>Sin registros de asistencia.</p>
          ) : (
            <ul>
              {asistencias.slice(0, 20).map((item, index) => (
                <li key={item.id || item.id_asistencia || `${item.fecha}-${index}`}>
                  {item.fecha || item.fecha_asistencia || 'Sin fecha'} - {item.estado || item.estado_display || 'Sin estado'}
                </li>
              ))}
            </ul>
          )}
        </article>
      ) : null}

      {activeTab === 'calendario' ? (
        <article className="card section-card">
          <h3>Calendario</h3>
          {annotationsLoading ? (
            <TableLoadingState />
          ) : anotaciones.length === 0 ? (
            <p>Sin eventos o anotaciones recientes.</p>
          ) : (
            <ul>
              {anotaciones.slice(0, 20).map((item, index) => (
                <li key={item.id || index}>{item.fecha || ''} {item.descripcion || item.contenido || item.tipo || 'Registro'}</li>
              ))}
            </ul>
          )}
        </article>
      ) : null}

      {activeTab === 'comunicados' ? (
        <article className="card section-card">
          <h3>Comunicados</h3>
          {comunicadosLoading ? (
            <TableLoadingState />
          ) : comunicados.length === 0 ? (
            <p>Sin comunicados recientes.</p>
          ) : (
            <ul className="compact-list">
              {comunicados.map((item) => {
                const comunicadoId = item.id_comunicado || item.id;
                return (
                  <li key={comunicadoId}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                      <strong>{item.titulo || item.nombre || 'Comunicado'}</strong>
                      <span style={{ color: 'var(--muted)' }}>{formatShortDate(item.fecha_publicacion || item.fecha, '-')}</span>
                    </div>
                    <p style={{ margin: '0.5rem 0' }}>{item.contenido || item.descripcion || 'Sin detalle disponible.'}</p>
                    {item.requiere_confirmacion ? (
                      <button
                        type="button"
                        onClick={() => onConfirmComunicado(comunicadoId)}
                        disabled={confirmingComunicadoId === comunicadoId}
                      >
                        {confirmingComunicadoId === comunicadoId ? 'Confirmando...' : 'Confirmar lectura'}
                      </button>
                    ) : (
                      <span style={{ color: 'var(--muted)' }}>Solo lectura</span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </article>
      ) : null}

      {activeTab === 'mensajes' ? (
        <article className="card section-card">
          <h3>Mensajes</h3>
          {conversationsLoading ? (
            <TableLoadingState />
          ) : conversaciones.length === 0 ? (
            <p>Sin conversaciones disponibles.</p>
          ) : (
            <>
              <label>
                Conversacion
                <select value={selectedConversationId} onChange={(event) => onConversationChange(event.target.value)}>
                  <option value="">Seleccionar</option>
                  {conversaciones.map((item) => {
                    const convId = item.id_conversacion || item.id;
                    const unread = item.no_leidos ? ` (${item.no_leidos})` : '';
                    return (
                      <option key={convId} value={convId}>
                        {item.otro_participante_nombre || 'Conversacion'}{unread}
                      </option>
                    );
                  })}
                </select>
              </label>

              {messagesLoading ? (
                <TableLoadingState />
              ) : mensajes.length === 0 ? (
                <p>Sin mensajes para esta conversacion.</p>
              ) : (
                <ul className="compact-list" style={{ marginTop: '1rem' }}>
                  {mensajes.slice(-15).map((item) => (
                    <li key={item.id_mensaje || item.id}>
                      <strong>{item.emisor_nombre || 'Usuario'}</strong>
                      <span> - {formatShortDate(item.fecha_envio, '-')}</span>
                      <p style={{ margin: '0.35rem 0 0' }}>{item.contenido || 'Sin contenido'}</p>
                      {item.archivo_adjunto ? (
                        <a href={item.archivo_adjunto} target="_blank" rel="noreferrer">Ver adjunto</a>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </article>
      ) : null}

      {activeTab === 'certificados' ? (
        <article className="card section-card">
          <h3>Certificados</h3>
          {pupilsLoading ? (
            <TableLoadingState />
          ) : pupilos.length === 0 ? (
            <p>Sin pupilos vinculados para certificados.</p>
          ) : (
            <ul className="compact-list">
              {pupilos.map((item) => {
                const studentId = getPupilId(item);
                return (
                  <li key={studentId}>
                    <strong>{getPupilName(item)}</strong>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginTop: '0.5rem' }}>
                      <a href={buildPdfUrl(studentId, 'certificado-notas')} target="_blank" rel="noreferrer">Certificado de notas</a>
                      <a href={buildPdfUrl(studentId, 'certificado-matricula')} target="_blank" rel="noreferrer">Certificado de matricula</a>
                      <a href={buildPdfUrl(studentId, 'informe-rendimiento')} target="_blank" rel="noreferrer">Informe de rendimiento</a>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </article>
      ) : null}

      {activeTab === 'admision' ? (
        <div className="grid-2">
          <form className="card section-card form-grid" onSubmit={onAdmissionSubmit}>
            <h3>Solicitud de admision</h3>
            {admissionResult ? (
              <p role="status" style={{ color: admissionResult.type === 'error' ? '#b91c1c' : '#15803d', margin: 0 }}>
                {admissionResult.message}
              </p>
            ) : null}
            <label>
              Curso ID
              <input
                type="number"
                min="1"
                value={admissionForm.curso_id}
                onChange={(event) => onAdmissionChange('curso_id', event.target.value)}
                required
                disabled={admissionSaving}
              />
            </label>
            <label>
              Ciclo ID
              <input
                type="number"
                min="1"
                value={admissionForm.ciclo_id}
                onChange={(event) => onAdmissionChange('ciclo_id', event.target.value)}
                required
                disabled={admissionSaving}
              />
            </label>
            <label>
              Nombre estudiante
              <input
                value={admissionForm.nombre_estudiante}
                onChange={(event) => onAdmissionChange('nombre_estudiante', event.target.value)}
                required
                disabled={admissionSaving}
              />
            </label>
            <label>
              Apellido paterno
              <input
                value={admissionForm.apellido_paterno_estudiante}
                onChange={(event) => onAdmissionChange('apellido_paterno_estudiante', event.target.value)}
                required
                disabled={admissionSaving}
              />
            </label>
            <label>
              Apellido materno
              <input
                value={admissionForm.apellido_materno_estudiante}
                onChange={(event) => onAdmissionChange('apellido_materno_estudiante', event.target.value)}
                required
                disabled={admissionSaving}
              />
            </label>
            <label>
              RUT estudiante
              <input
                value={admissionForm.rut_estudiante}
                onChange={(event) => onAdmissionChange('rut_estudiante', event.target.value)}
                disabled={admissionSaving}
              />
            </label>
            <label>
              Fecha nacimiento
              <input
                type="date"
                value={admissionForm.fecha_nacimiento_estudiante}
                onChange={(event) => onAdmissionChange('fecha_nacimiento_estudiante', event.target.value)}
                disabled={admissionSaving}
              />
            </label>
            <label>
              Genero
              <select
                value={admissionForm.genero_estudiante}
                onChange={(event) => onAdmissionChange('genero_estudiante', event.target.value)}
                disabled={admissionSaving}
              >
                <option value="O">Otro</option>
                <option value="F">Femenino</option>
                <option value="M">Masculino</option>
              </select>
            </label>
            <label>
              Direccion hogar
              <input
                value={admissionForm.direccion_hogar}
                onChange={(event) => onAdmissionChange('direccion_hogar', event.target.value)}
                disabled={admissionSaving}
              />
            </label>
            <label>
              Telefono contacto
              <input
                value={admissionForm.telefono_contacto}
                onChange={(event) => onAdmissionChange('telefono_contacto', event.target.value)}
                disabled={admissionSaving}
              />
            </label>
            <label>
              Parentesco
              <select
                value={admissionForm.parentesco}
                onChange={(event) => onAdmissionChange('parentesco', event.target.value)}
                disabled={admissionSaving}
              >
                <option value="PADRE">Padre</option>
                <option value="MADRE">Madre</option>
                <option value="TUTOR">Tutor</option>
                <option value="OTRO">Otro</option>
              </select>
            </label>
            <label>
              Certificado nacimiento
              <input
                type="file"
                accept="application/pdf,image/*"
                onChange={(event) => onAdmissionChange('certificado_nacimiento', event.target.files?.[0] || null)}
                disabled={admissionSaving}
              />
            </label>
            <label>
              Certificado medico
              <input
                type="file"
                accept="application/pdf,image/*"
                onChange={(event) => onAdmissionChange('certificado_medico', event.target.files?.[0] || null)}
                disabled={admissionSaving}
              />
            </label>
            <div>
              <button type="submit" disabled={admissionSaving}>
                {admissionSaving ? 'Enviando...' : 'Enviar solicitud'}
              </button>
            </div>
          </form>

          <form className="card section-card form-grid" onSubmit={onContractSubmit}>
            <h3>Firma de contrato</h3>
            {contractResult ? (
              <p role="status" style={{ color: contractResult.type === 'error' ? '#b91c1c' : '#15803d', margin: 0 }}>
                {contractResult.message}
              </p>
            ) : null}
            <label>
              Solicitud ID
              <input
                type="number"
                min="1"
                value={contractForm.solicitud_id}
                onChange={(event) => onContractChange('solicitud_id', event.target.value)}
                required
                disabled={contractSaving}
              />
            </label>
            <label>
              RUT firmante
              <input
                value={contractForm.rut_firmante}
                onChange={(event) => onContractChange('rut_firmante', event.target.value)}
                required
                disabled={contractSaving}
              />
            </label>
            <div>
              <button type="submit" disabled={contractSaving}>
                {contractSaving ? 'Firmando...' : 'Firmar contrato'}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {activeTab === 'estado_cuenta' ? (
        <article className="card section-card">
          <h3>Estado de cuenta</h3>
          {pagosLoading ? (
            <TableLoadingState />
          ) : pagosError ? (
            <div className="error-box" role="alert" aria-live="assertive">{pagosError}</div>
          ) : pagosPupilos.length === 0 ? (
            <p>Sin estado de cuenta disponible.</p>
          ) : (
            <>
              <div className="summary-grid" style={{ marginBottom: '1rem' }}>
                <article className="summary-tile">
                  <small>Total deuda</small>
                  <strong>{formatNumber(pagosResumen?.total_deuda, '0')}</strong>
                  <span>Deuda acumulada</span>
                </article>
                <article className="summary-tile">
                  <small>Total pagado</small>
                  <strong>{formatNumber(pagosResumen?.total_pagado, '0')}</strong>
                  <span>Pagos registrados</span>
                </article>
                <article className="summary-tile">
                  <small>Saldo pendiente</small>
                  <strong>{formatNumber(pagosResumen?.saldo_pendiente, '0')}</strong>
                  <span>Saldo por regularizar</span>
                </article>
              </div>
              <ul className="compact-list">
                {pagosPupilos.map((item) => (
                  <li key={item.student_id || item.id}>
                    <strong>{item.nombre_completo || 'Pupilo'}</strong>
                    <span> - Saldo: {formatNumber(item.saldo_pendiente, '0')}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </article>
      ) : null}

      {activeTab === 'mis_pagos' ? (
        <article className="card section-card">
          <h3>Mis pagos</h3>
          {pagosLoading ? (
            <TableLoadingState />
          ) : pagosError ? (
            <div className="error-box" role="alert" aria-live="assertive">{pagosError}</div>
          ) : pagosPupilos.length === 0 ? (
            <p>Sin pagos registrados.</p>
          ) : (
            <ul className="compact-list">
              {pagosPupilos.map((item) => (
                <li key={item.student_id || item.id}>
                  <strong>{item.nombre_completo || 'Pupilo'}</strong>
                  <span> - Pagado: {formatNumber(item.total_pagado, '0')} | Pendiente: {formatNumber(item.saldo_pendiente, '0')}</span>
                </li>
              ))}
            </ul>
          )}
          <p style={{ marginTop: '0.75rem', color: 'var(--muted)' }}>Para el detalle completo de pagos y comprobantes, consulta con el area administrativa del colegio.</p>
        </article>
      ) : null}

      {activeTab === 'perfil' ? (
        <article className="card section-card">
          <h3>Mi perfil</h3>
          {profileLoading ? (
            <TableLoadingState />
          ) : profileError ? (
            <div className="error-box" role="alert" aria-live="assertive">{profileError}</div>
          ) : (
            <>
              <dl className="detail-list">
                <div>
                  <dt>Nombre</dt>
                  <dd>{profileName}</dd>
                </div>
                <div>
                  <dt>Correo</dt>
                  <dd>{profileUser.email || profileUser.correo || 'Sin correo'}</dd>
                </div>
                <div>
                  <dt>RUT</dt>
                  <dd>{profileUser.rut || 'Sin RUT'}</dd>
                </div>
                <div>
                  <dt>Telefono</dt>
                  <dd>{profile?.telefono || profile?.telefono_movil || 'Sin telefono'}</dd>
                </div>
                <div>
                  <dt>Direccion</dt>
                  <dd>{profile?.direccion || 'Sin direccion'}</dd>
                </div>
              </dl>
              {profilePupilos.length ? (
                <div style={{ marginTop: '1rem' }}>
                  <strong>Estudiantes vinculados</strong>
                  <ul className="compact-list" style={{ marginTop: '0.5rem' }}>
                    {profilePupilos.map((item) => (
                      <li key={item.id}>
                        {item.nombre} {item.parentesco ? `- ${item.parentesco}` : ''}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          )}
        </article>
      ) : null}

      {['resumen', 'justificativos', 'firmas'].includes(activeTab) ? (
      <>
      <div className="grid-2">
        <article className="card section-card">
          <h3>Justificativos ({justificativos.length})</h3>
          {loading ? (
            <TableLoadingState />
          ) : justificativos.length === 0 ? (
            <p>Sin justificativos.</p>
          ) : (
            <ul>
              {justificativos.slice(0, 10).map((item) => (
                <li key={item.id || item.id_justificativo}>
                  {item.fecha_ausencia || item.fecha || 'Sin fecha'} - {item.estado || 'Pendiente'}
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="card section-card">
          <h3>Firmas</h3>
          {loading ? (
            <TableLoadingState />
          ) : (
            <>
              <p>Pendientes: {pendientes.length}</p>
              <p>Firmados: {firmados.length}</p>
            </>
          )}
        </article>
      </div>

      <form className="card section-card form-grid" onSubmit={onSign}>
      <h3>Firmar documento</h3>

        <label>
          Tipo documento
          <input value={signForm.tipo_documento} onChange={(e) => onChange('tipo_documento', e.target.value)} disabled={saving} required />
        </label>

        <label>
          Titulo
          <input value={signForm.titulo} onChange={(e) => onChange('titulo', e.target.value)} disabled={saving} required />
        </label>

        <label>
          Contenido
          <textarea value={signForm.contenido} onChange={(e) => onChange('contenido', e.target.value)} disabled={saving} />
        </label>

        <label>
          Estudiante ID (opcional)
          <input
            type="number"
            min="1"
            value={signForm.estudiante_id}
            onChange={(e) => onChange('estudiante_id', e.target.value)}
            disabled={saving}
          />
        </label>

        <div>
          <button type="submit" disabled={saving || !signForm.tipo_documento || !signForm.titulo}>
            {saving ? 'Firmando...' : 'Firmar'}
          </button>
        </div>
      </form>
      </>
      ) : null}
    </section>
  );
}

