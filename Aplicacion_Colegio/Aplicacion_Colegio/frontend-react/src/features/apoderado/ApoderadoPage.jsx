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
  const [newMessage, setNewMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [selectedCuotaForPayment, setSelectedCuotaForPayment] = useState(null);
  const [webpayCardNumber, setWebpayCardNumber] = useState('');
  const [webpayExpiry, setWebpayExpiry] = useState('');
  const [webpayCvv, setWebpayCvv] = useState('');
  const [webpayProcessing, setWebpayProcessing] = useState(false);
  const [selectedAttendanceItem, setSelectedAttendanceItem] = useState(null);
  const [attendanceFilter, setAttendanceFilter] = useState('ALL');
  const [justificationModalOpen, setJustificationModalOpen] = useState(false);
  const [justificationForm, setJustificationForm] = useState({
    fecha_ausencia: '',
    motivo: '',
    tipo: 'MEDICO',
  });
  const [submittingJustification, setSubmittingJustification] = useState(false);
  const [calDate, setCalDate] = useState(new Date());
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

  const handleDownloadPdf = async (studentId, path, docName) => {
    try {
      const blob = await apiClient.downloadBlob(`/api/v1/pdf/${path}/${studentId}/`);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${docName}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('No se pudo descargar el certificado.');
    }
  };

  const { data: justData, isLoading: justLoading, error: justErrorObj } = useQuery({
    queryKey: ['apoderado-justificativos'],
    queryFn: () => apiClient.get('/api/v1/apoderado/justificativos/')
  });
  const { data: signData, isLoading: signLoading, error: signErrorObj } = useQuery({
    queryKey: ['apoderado-firmas'],
    queryFn: () => apiClient.get('/api/v1/apoderado/firmas/')
  });
  const { data: admissionOptions } = useQuery({
    queryKey: ['apoderado-admision-opciones'],
    queryFn: () => apiClient.get('/api/v1/apoderado/admision/opciones/')
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
  const { data: estadoCuenta, isLoading: loadingEstadoCuenta } = useQuery({
    queryKey: ['apoderado-estado-cuenta', selectedPupilId],
    queryFn: () => apiClient.get(`/api/v1/estudiante/estado-cuenta/?estudiante_id=${selectedPupilId}`),
    enabled: Boolean(selectedPupilId) && (activeTab === 'estado_cuenta' || activeTab === 'mis_pagos')
  });
  const { data: misPagos, isLoading: loadingMisPagos } = useQuery({
    queryKey: ['apoderado-mis-pagos', selectedPupilId],
    queryFn: () => apiClient.get(`/api/v1/estudiante/mis-pagos/?estudiante_id=${selectedPupilId}`),
    enabled: Boolean(selectedPupilId) && (activeTab === 'estado_cuenta' || activeTab === 'mis_pagos')
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
      const payload = await apiClient.post('/api/v1/apoderado/firmas/firmar/', {
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

  async function handleSendMessage(e) {
    e.preventDefault();
    if (!newMessage.trim() || !selectedConversationId) return;
    setSendingMessage(true);
    try {
      await apiClient.post(`/api/v1/mensajeria/conversaciones/${selectedConversationId}/mensajes/`, {
        contenido: newMessage.trim()
      });
      setNewMessage('');
      toast.success('Mensaje enviado con éxito.');
      await queryClient.invalidateQueries({ queryKey: ['apoderado-mensajes', selectedConversationId] });
      await queryClient.invalidateQueries({ queryKey: ['apoderado-conversaciones'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo enviar el mensaje.'));
    } finally {
      setSendingMessage(false);
    }
  }

  function handleOpenWebpay(cuota) {
    setSelectedCuotaForPayment(cuota);
    setWebpayCardNumber('4540 1234 5678 9012');
    setWebpayExpiry('12/29');
    setWebpayCvv('123');
  }

  async function handleProcessWebpay(e) {
    e.preventDefault();
    if (!selectedCuotaForPayment) return;
    setWebpayProcessing(true);
    try {
      await apiClient.post('/api/v1/estudiante/pagos/crear/', {
        cuota_id: selectedCuotaForPayment.id_cuota,
        numero_transaccion: 'TX-WP-' + Math.floor(Math.random() * 10000000),
        numero_comprobante: 'COM-' + Math.floor(Math.random() * 10000000)
      });
      toast.success('¡Pago procesado con éxito por Webpay Transbank!');
      setSelectedCuotaForPayment(null);
      await queryClient.invalidateQueries({ queryKey: ['apoderado-estado-cuenta', selectedPupilId] });
      await queryClient.invalidateQueries({ queryKey: ['apoderado-mis-pagos', selectedPupilId] });
    } catch (err) {
      toast.error(resolveError(err, 'Ocurrió un error al procesar el pago.'));
    } finally {
      setWebpayProcessing(false);
    }
  }

  async function handleSubmitJustification(e) {
    e.preventDefault();
    if (!justificationForm.fecha_ausencia || !justificationForm.motivo || !selectedPupilId) return;
    setSubmittingJustification(true);
    try {
      await apiClient.post('/api/v1/apoderado/justificativos/', {
        estudiante_id: Number(selectedPupilId),
        fecha_ausencia: justificationForm.fecha_ausencia,
        motivo: justificationForm.motivo,
        tipo: justificationForm.tipo
      });
      toast.success('Justificativo enviado correctamente.');
      setJustificationForm({ fecha_ausencia: '', motivo: '', tipo: 'MEDICO' });
      setJustificationModalOpen(false);
      await queryClient.invalidateQueries({ queryKey: ['apoderado-justificativos'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo enviar el justificativo.'));
    } finally {
      setSubmittingJustification(false);
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

      const payload = await apiClient.postFormData('/api/apoderado/admisiones/solicitar/', formData);

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
      setAdmissionResult({ type: 'error', message: resolveError(err, 'No se pudo enviar la solicitud.') });
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
            <h3 style={{ margin: 0 }}>Asistencia {selectedPupil ? `de ${getPupilName(selectedPupil)}` : ''}</h3>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {['ALL', 'P', 'A', 'T', 'J'].map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setAttendanceFilter(f)}
                  className={`badge ${attendanceFilter === f ? 'badge-warning' : 'badge-inactive'}`}
                  style={{ border: 'none', cursor: 'pointer', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                >
                  {f === 'ALL' ? 'Todos' : f === 'P' ? 'Presentes' : f === 'A' ? 'Ausentes' : f === 'T' ? 'Atrasos' : 'Justificados'}
                </button>
              ))}
            </div>
          </div>

          {attendanceLoading ? (
            <TableLoadingState />
          ) : (
            <>
              {attendanceData?.resumen && (
                <div className="summary-grid" style={{ marginBottom: '1.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))' }}>
                  <article className="summary-tile" style={{ padding: '0.75rem' }}>
                    <small>Asistencia</small>
                    <strong style={{ fontSize: '1.5rem', color: attendanceData.resumen.porcentaje_asistencia >= 85 ? '#10b981' : '#ef4444' }}>
                      {attendanceData.resumen.porcentaje_asistencia}%
                    </strong>
                    <span>Tasa de asistencia</span>
                  </article>
                  <article className="summary-tile" style={{ padding: '0.75rem' }}>
                    <small>Presentes</small>
                    <strong style={{ fontSize: '1.5rem' }}>{attendanceData.resumen.presentes}</strong>
                    <span>Clases asistidas</span>
                  </article>
                  <article className="summary-tile" style={{ padding: '0.75rem' }}>
                    <small>Ausentes</small>
                    <strong style={{ fontSize: '1.5rem', color: '#ef4444' }}>{attendanceData.resumen.ausentes}</strong>
                    <span>Clases inasistentes</span>
                  </article>
                  <article className="summary-tile" style={{ padding: '0.75rem' }}>
                    <small>Atrasos</small>
                    <strong style={{ fontSize: '1.5rem', color: '#f59e0b' }}>{attendanceData.resumen.tardanzas}</strong>
                    <span>Llegadas tarde</span>
                  </article>
                </div>
              )}

              {asistencias.length === 0 ? (
                <p>Sin registros de asistencia.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Asignatura</th>
                        <th>Estado</th>
                        <th>Acción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {asistencias
                        .filter(item => attendanceFilter === 'ALL' || item.estado === attendanceFilter)
                        .slice(0, 20)
                        .map((item, index) => {
                          const statusColor = item.estado === 'P' ? '#10b981' : item.estado === 'A' ? '#ef4444' : item.estado === 'T' ? '#f59e0b' : '#3b82f6';
                          return (
                            <tr key={item.id || item.id_asistencia || `${item.fecha}-${index}`}>
                              <td>{formatShortDate(item.fecha || item.fecha_asistencia, '-')}</td>
                              <td>{item.asignatura || 'Clase'}</td>
                              <td>
                                <span style={{
                                  fontSize: '0.75rem',
                                  fontWeight: '600',
                                  padding: '0.2rem 0.5rem',
                                  borderRadius: '999px',
                                  background: `${statusColor}1c`,
                                  color: statusColor,
                                  border: `1px solid ${statusColor}40`
                                }}>
                                  {item.estado_display || item.estado}
                                </span>
                              </td>
                              <td>
                                <button
                                  type="button"
                                  onClick={() => setSelectedAttendanceItem(item)}
                                  className="badge badge-inactive"
                                  style={{ border: 'none', cursor: 'pointer' }}
                                >
                                  🔍 Ver Detalle
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </article>
      ) : null}

      {activeTab === 'calendario' ? (
        <article className="card section-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h3>Calendario de Eventos y Anotaciones</h3>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <button
                type="button"
                className="badge badge-inactive"
                style={{ border: 'none', cursor: 'pointer' }}
                onClick={() => setCalDate(new Date(calDate.getFullYear(), calDate.getMonth() - 1, 1))}
              >
                ‹ Anterior
              </button>
              <strong style={{ fontSize: '1rem', minWidth: '150px', textAlign: 'center' }}>
                {calDate.toLocaleString('es-ES', { month: 'long', year: 'numeric' }).toUpperCase()}
              </strong>
              <button
                type="button"
                className="badge badge-inactive"
                style={{ border: 'none', cursor: 'pointer' }}
                onClick={() => setCalDate(new Date(calDate.getFullYear(), calDate.getMonth() + 1, 1))}
              >
                Siguiente ›
              </button>
            </div>
          </div>

          {annotationsLoading ? (
            <TableLoadingState />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                gap: '4px',
                border: '1px solid rgba(148, 163, 184, 0.1)',
                borderRadius: '8px',
                padding: '4px',
                background: 'rgba(255,255,255,0.01)'
              }}>
                {['DOM', 'LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB'].map(d => (
                  <div key={d} style={{ textAlign: 'center', fontWeight: 'bold', fontSize: '0.75rem', padding: '0.5rem 0', color: 'var(--muted)' }}>{d}</div>
                ))}
                {(() => {
                  const days = [];
                  const year = calDate.getFullYear();
                  const month = calDate.getMonth();
                  const firstDay = new Date(year, month, 1);
                  const lastDay = new Date(year, month + 1, 0);
                  const startDay = firstDay.getDay();
                  const totalDays = lastDay.getDate();

                  for (let i = 0; i < startDay; i++) {
                    days.push(<div key={`empty-${i}`} style={{ minHeight: '60px', background: 'transparent' }} />);
                  }

                  for (let day = 1; day <= totalDays; day++) {
                    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                    const items = anotaciones.filter(item => (item.fecha || '').startsWith(dateStr));
                    const isToday = new Date().toDateString() === new Date(year, month, day).toDateString();

                    days.push(
                      <div key={day} style={{
                        minHeight: '60px',
                        border: '1px solid rgba(148, 163, 184, 0.08)',
                        borderRadius: '6px',
                        padding: '4px',
                        background: isToday ? 'rgba(59, 130, 246, 0.1)' : 'rgba(255, 255, 255, 0.02)',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        cursor: items.length > 0 ? 'pointer' : 'default',
                        boxShadow: isToday ? '0 0 10px rgba(59,130,246,0.2)' : undefined
                      }} onClick={() => items.length > 0 && setSelectedAttendanceItem({ ...items[0], type: 'ANOTACION' })}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: isToday ? '#3b82f6' : 'inherit' }}>{day}</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          {items.slice(0, 2).map((item, idx) => {
                            const isPositive = item.tipo === 'P' || item.gravedad === 'LEVE';
                            return (
                              <div key={idx} style={{
                                fontSize: '0.65rem',
                                padding: '2px 4px',
                                borderRadius: '3px',
                                background: isPositive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                                color: isPositive ? '#10b981' : '#ef4444',
                                textOverflow: 'ellipsis',
                                overflow: 'hidden',
                                whiteSpace: 'nowrap'
                              }} title={item.descripcion || item.contenido}>
                                {item.tipo_display || item.tipo || 'Anotación'}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  }
                  return days;
                })()}
              </div>

              <div>
                <h4 style={{ marginBottom: '0.75rem' }}>Listado de Anotaciones</h4>
                {anotaciones.length === 0 ? (
                  <p>Sin anotaciones registradas.</p>
                ) : (
                  <ul className="compact-list">
                    {anotaciones.slice(0, 10).map((item, index) => {
                      const isPositive = item.tipo === 'P' || item.gravedad === 'LEVE';
                      return (
                        <li key={item.id || index} style={{ borderLeft: `4px solid ${isPositive ? '#10b981' : '#ef4444'}`, paddingLeft: '1rem', marginBottom: '0.5rem' }}>
                          <div style={{ display: 'flex', justifycontent: 'space-between', alignItems: 'center' }}>
                            <strong>{item.tipo_display || item.tipo || 'Anotación de Convivencia'}</strong>
                            <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{formatShortDate(item.fecha, '-')}</span>
                          </div>
                          <p style={{ margin: '0.25rem 0', fontSize: '0.9rem' }}>{item.descripcion || item.contenido}</p>
                          <small style={{ color: 'var(--muted)' }}>Registrado por: {item.registrado_por || 'Establecimiento'}</small>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>
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
              ) : (
                <>
                  {mensajes.length === 0 ? (
                    <p>Sin mensajes para esta conversacion.</p>
                  ) : (
                    <ul className="compact-list" style={{ marginTop: '1rem', maxHeight: '300px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                      {mensajes.slice(-15).map((item) => (
                        <li key={item.id_mensaje || item.id} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginBottom: '0.75rem', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255, 255, 255, 0.02)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <strong style={{ fontSize: '0.9rem', color: 'var(--primary)' }}>{item.emisor_nombre || 'Usuario'}</strong>
                            <small style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{formatShortDate(item.fecha_envio, '-')}</small>
                          </div>
                          <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--foreground)' }}>{item.contenido || 'Sin contenido'}</p>
                          {item.archivo_adjunto ? (
                            <a href={item.archivo_adjunto} target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem', color: 'var(--primary)', marginTop: '0.25rem' }}>📎 Ver adjunto</a>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                  <form onSubmit={handleSendMessage} style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
                    <input
                      type="text"
                      placeholder="Escribe un mensaje..."
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      disabled={sendingMessage}
                      style={{ flex: 1, padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.2)', background: 'rgba(255, 255, 255, 0.05)', color: 'inherit' }}
                    />
                    <button type="submit" disabled={sendingMessage || !newMessage.trim()} className="badge badge-warning" style={{ border: 'none', cursor: 'pointer', padding: '0 1.25rem' }}>
                      {sendingMessage ? 'Enviando...' : 'Enviar'}
                    </button>
                  </form>
                </>
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
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          handleDownloadPdf(studentId, 'certificado-notas', `Certificado_Notas_${studentId}`);
                        }}
                      >
                        Certificado de notas
                      </a>
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          handleDownloadPdf(studentId, 'certificado-matricula', `Certificado_Matricula_${studentId}`);
                        }}
                      >
                        Certificado de matrícula
                      </a>
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          handleDownloadPdf(studentId, 'informe-rendimiento', `Informe_Rendimiento_${studentId}`);
                        }}
                      >
                        Informe de rendimiento
                      </a>
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
              Curso
              <select
                value={admissionForm.curso_id}
                onChange={(event) => onAdmissionChange('curso_id', event.target.value)}
                required
                disabled={admissionSaving}
                style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.2)', background: 'rgba(255, 255, 255, 0.05)', color: 'inherit' }}
              >
                <option value="">Seleccione un curso...</option>
                {admissionOptions?.cursos?.map((c) => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
            </label>
            <label>
              Ciclo Académico
              <select
                value={admissionForm.ciclo_id}
                onChange={(event) => onAdmissionChange('ciclo_id', event.target.value)}
                required
                disabled={admissionSaving}
                style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.2)', background: 'rgba(255, 255, 255, 0.05)', color: 'inherit' }}
              >
                <option value="">Seleccione un ciclo...</option>
                {admissionOptions?.ciclos?.map((c) => (
                  <option key={c.id} value={c.id}>{c.nombre} {c.estado === 'ACTIVO' ? '(Activo)' : ''}</option>
                ))}
              </select>
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
          <h3>Estado de cuenta {selectedPupil ? `de ${getPupilName(selectedPupil)}` : ''}</h3>
          {loadingEstadoCuenta ? (
            <TableLoadingState />
          ) : pagosError ? (
            <div className="error-box" role="alert" aria-live="assertive">{pagosError}</div>
          ) : !estadoCuenta?.totales ? (
            <p>Sin estado de cuenta disponible.</p>
          ) : (
            <>
              <div className="summary-grid" style={{ marginBottom: '1.5rem' }}>
                <article className="summary-tile">
                  <small>Total arancel</small>
                  <strong>{formatNumber(estadoCuenta.totales.total_arancel, '0')}</strong>
                  <span>Arancel del ciclo</span>
                </article>
                <article className="summary-tile">
                  <small>Descuentos</small>
                  <strong>{formatNumber(estadoCuenta.totales.total_descuentos, '0')}</strong>
                  <span>Beneficios aplicados</span>
                </article>
                <article className="summary-tile">
                  <small>Total a pagar</small>
                  <strong>{formatNumber(estadoCuenta.totales.total_a_pagar, '0')}</strong>
                  <span>Monto neto</span>
                </article>
                <article className="summary-tile">
                  <small>Total pagado</small>
                  <strong>{formatNumber(estadoCuenta.totales.total_pagado, '0')}</strong>
                  <span>Abonos</span>
                </article>
                <article className="summary-tile" style={{ background: estadoCuenta.totales.saldo_pendiente > 0 ? 'rgba(239, 68, 68, 0.08)' : undefined }}>
                  <small style={{ color: estadoCuenta.totales.saldo_pendiente > 0 ? '#ef4444' : undefined }}>Saldo pendiente</small>
                  <strong style={{ color: estadoCuenta.totales.saldo_pendiente > 0 ? '#ef4444' : undefined }}>{formatNumber(estadoCuenta.totales.saldo_pendiente, '0')}</strong>
                  <span>Saldo por regularizar</span>
                </article>
              </div>

              <div style={{ marginTop: '0.5rem' }}>
                <h4 style={{ marginBottom: '1rem' }}>Detalle de Cuotas</h4>
                {(!estadoCuenta.cuotas || estadoCuenta.cuotas.length === 0) ? (
                  <p>No hay cuotas registradas.</p>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Cuota</th>
                          <th>Año/Mes</th>
                          <th>Monto Final</th>
                          <th>Pagado</th>
                          <th>Saldo Pendiente</th>
                          <th>Vencimiento</th>
                          <th>Estado</th>
                          <th>Acción</th>
                        </tr>
                      </thead>
                      <tbody>
                        {estadoCuenta.cuotas.map((cuota) => {
                          const colorMap = {
                            PAGADA: '#10b981',
                            PENDIENTE: '#6b7280',
                            VENCIDA: '#ef4444',
                            PAGADA_PARCIAL: '#f59e0b',
                          };
                          const color = colorMap[cuota.estado] || '#6b7280';
                          return (
                            <tr key={cuota.id_cuota}>
                              <td>Cuota #{cuota.numero_cuota}</td>
                              <td>{cuota.anio} / {String(cuota.mes).padStart(2, '0')}</td>
                              <td>${formatNumber(cuota.monto_final, '0')}</td>
                              <td>${formatNumber(cuota.monto_pagado, '0')}</td>
                              <td>
                                <strong style={{ color: cuota.saldo_pendiente > 0 ? '#ef4444' : undefined }}>
                                  ${formatNumber(cuota.saldo_pendiente, '0')}
                                </strong>
                              </td>
                              <td>{cuota.fecha_vencimiento ? new Date(cuota.fecha_vencimiento + 'T00:00:00').toLocaleDateString() : '-'}</td>
                              <td>
                                <span style={{
                                  fontSize: '0.75rem',
                                  fontWeight: '600',
                                  padding: '0.2rem 0.5rem',
                                  borderRadius: '999px',
                                  background: `${color}1c`,
                                  color,
                                  border: `1px solid ${color}40`,
                                  display: 'inline-block'
                                }}>
                                  {cuota.estado}
                                </span>
                              </td>
                              <td>
                                {cuota.saldo_pendiente > 0 && cuota.estado !== 'PAGADA' ? (
                                  <button
                                    type="button"
                                    onClick={() => handleOpenWebpay(cuota)}
                                    className="badge badge-warning"
                                    style={{ border: 'none', cursor: 'pointer' }}
                                  >
                                    💳 Pagar
                                  </button>
                                ) : (
                                  <span style={{ color: '#10b981', fontSize: '0.85rem', fontWeight: '600' }}>✓ Pagado</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </article>
      ) : null}

      {activeTab === 'mis_pagos' ? (
        <article className="card section-card">
          <h3>Historial de Pagos de {selectedPupil ? getPupilName(selectedPupil) : ''}</h3>
          {loadingMisPagos ? (
            <TableLoadingState />
          ) : pagosError ? (
            <div className="error-box" role="alert" aria-live="assertive">{pagosError}</div>
          ) : !misPagos ? (
            <p>Sin pagos registrados.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div className="summary-grid" style={{ gridTemplateColumns: '1fr' }}>
                <article className="summary-tile" style={{ maxWidth: '300px' }}>
                  <small>Monto Total Pagado</small>
                  <strong style={{ color: '#10b981' }}>${formatNumber(misPagos.total_pagado, '0')}</strong>
                  <span>Total de abonos a la fecha</span>
                </article>
              </div>

              <div style={{ marginTop: '0.5rem' }}>
                <h4 style={{ marginBottom: '1rem' }}>Pagos Registrados</h4>
                {(!misPagos.pagos || misPagos.pagos.length === 0) ? (
                  <p>Aún no registra abonos o pagos asociados.</p>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Comprobante</th>
                          <th>Fecha</th>
                          <th>Monto</th>
                          <th>Método de Pago</th>
                          <th>Transacción</th>
                          <th>Estado</th>
                          <th>Archivo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {misPagos.pagos.map((pago) => {
                          const isSuccess = pago.estado === 'APROBADO' || pago.estado === 'PROCESADO' || pago.estado === 'COMPLETADO' || pago.estado === 'Aprobado';
                          const color = isSuccess ? '#10b981' : '#6b7280';
                          return (
                            <tr key={pago.id_pago}>
                              <td>#{pago.numero_comprobante || pago.id_pago}</td>
                              <td>{pago.fecha_pago ? new Date(pago.fecha_pago).toLocaleString() : '-'}</td>
                              <td>
                                <strong style={{ color: '#10b981' }}>${formatNumber(pago.monto, '0')}</strong>
                              </td>
                              <td>{pago.metodo_pago || 'N/A'}</td>
                              <td>{pago.numero_transaccion || '-'}</td>
                              <td>
                                <span style={{
                                  fontSize: '0.75rem',
                                  fontWeight: '600',
                                  padding: '0.2rem 0.5rem',
                                  borderRadius: '999px',
                                  background: `${color}1c`,
                                  color,
                                  border: `1px solid ${color}40`,
                                  display: 'inline-block'
                                }}>
                                  {pago.estado || 'Aprobado'}
                                </span>
                              </td>
                              <td>
                                {pago.comprobante ? (
                                  <a href={`${apiClient.baseUrl}${pago.comprobante}`} target="_blank" rel="noreferrer" style={{ fontSize: '0.85rem', color: 'var(--primary)' }}>
                                    📄 Ver Documento
                                  </a>
                                ) : '-'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Justificativos ({justificativos.length})</h3>
            {selectedPupilId && (
              <button
                type="button"
                onClick={() => setJustificationModalOpen(true)}
                className="badge badge-warning"
                style={{ border: 'none', cursor: 'pointer' }}
              >
                + Nuevo Justificativo
              </button>
            )}
          </div>
          {loading ? (
            <TableLoadingState />
          ) : justificativos.length === 0 ? (
            <p>Sin justificativos.</p>
          ) : (
            <ul className="compact-list">
              {justificativos.slice(0, 10).map((item) => {
                const color = item.estado === 'APROBADO' ? '#10b981' : item.estado === 'RECHAZADO' ? '#ef4444' : '#6b7280';
                return (
                  <li key={item.id || item.id_justificativo}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong>📅 {formatShortDate(item.fecha_ausencia || item.fecha, '-')}</strong>
                      <span style={{
                        fontSize: '0.7rem',
                        fontWeight: '600',
                        padding: '0.15rem 0.4rem',
                        borderRadius: '999px',
                        background: `${color}1c`,
                        color,
                        border: `1px solid ${color}40`
                      }}>
                        {item.estado}
                      </span>
                    </div>
                    <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>{item.motivo}</p>
                  </li>
                );
              })}
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
      {/* Modales Apoderado */}
      {selectedAttendanceItem && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '1rem'
        }}>
          <div style={{
            background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 0.98))',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '16px',
            padding: '2rem',
            width: '100%',
            maxWidth: '480px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
            color: '#f8fafc'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '1rem' }}>
              <h3 style={{ margin: 0 }}>
                {selectedAttendanceItem.type === 'ANOTACION' ? '📋 Detalle de Anotación' : '📅 Detalle de Asistencia'}
              </h3>
              <button
                type="button"
                onClick={() => setSelectedAttendanceItem(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.5rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>
            {selectedAttendanceItem.type === 'ANOTACION' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <p><strong>Categoría:</strong> {selectedAttendanceItem.categoria || 'Convivencia'}</p>
                <p><strong>Gravedad:</strong> {selectedAttendanceItem.gravedad || 'Leve'}</p>
                <p><strong>Fecha:</strong> {formatShortDate(selectedAttendanceItem.fecha, '-')}</p>
                <p><strong>Descripción:</strong> {selectedAttendanceItem.descripcion}</p>
                <p><strong>Registrado por:</strong> {selectedAttendanceItem.registrado_por || 'Colegio'}</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <p><strong>Fecha:</strong> {formatShortDate(selectedAttendanceItem.fecha || selectedAttendanceItem.fecha_asistencia, '-')}</p>
                <p><strong>Asignatura:</strong> {selectedAttendanceItem.asignatura || 'Clase'}</p>
                <p><strong>Estado:</strong> {selectedAttendanceItem.estado_display || selectedAttendanceItem.estado}</p>
                <p><strong>Tipo:</strong> {selectedAttendanceItem.tipo_asistencia || 'Normal'}</p>
                <p><strong>Observaciones:</strong> {selectedAttendanceItem.observaciones || 'Sin observaciones.'}</p>
              </div>
            )}
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="badge badge-inactive"
                onClick={() => setSelectedAttendanceItem(null)}
                style={{ border: 'none', cursor: 'pointer', padding: '0.5rem 1.5rem' }}
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {justificationModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '1rem'
        }}>
          <div style={{
            background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 0.98))',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '16px',
            padding: '2rem',
            width: '100%',
            maxWidth: '480px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
            color: '#f8fafc'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '1rem' }}>
              <h3 style={{ margin: 0 }}>📋 Presentar Justificativo</h3>
              <button
                type="button"
                onClick={() => setJustificationModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.5rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>
            <form onSubmit={handleSubmitJustification} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.35rem' }}>Fecha de Inasistencia</label>
                <input
                  type="date"
                  required
                  disabled={submittingJustification}
                  value={justificationForm.fecha_ausencia}
                  onChange={(e) => setJustificationForm(prev => ({ ...prev, fecha_ausencia: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    background: 'rgba(15, 23, 42, 0.6)',
                    color: '#f8fafc',
                    fontSize: '1rem'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.35rem' }}>Tipo de Inasistencia</label>
                <select
                  disabled={submittingJustification}
                  value={justificationForm.tipo}
                  onChange={(e) => setJustificationForm(prev => ({ ...prev, tipo: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    background: 'rgba(15, 23, 42, 0.6)',
                    color: '#f8fafc',
                    fontSize: '1rem'
                  }}
                >
                  <option value="MEDICO">Médica / Salud</option>
                  <option value="PERSONAL">Familiar / Personal</option>
                  <option value="FUERZA_MAYOR">Fuerza Mayor</option>
                  <option value="OTRO">Otro</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.35rem' }}>Motivo detallado</label>
                <textarea
                  required
                  disabled={submittingJustification}
                  value={justificationForm.motivo}
                  onChange={(e) => setJustificationForm(prev => ({ ...prev, motivo: e.target.value }))}
                  placeholder="Detalla la justificación de la ausencia..."
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    background: 'rgba(15, 23, 42, 0.6)',
                    color: '#f8fafc',
                    fontSize: '1rem',
                    height: '100px',
                    resize: 'none'
                  }}
                />
              </div>
              <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
                <button
                  type="button"
                  onClick={() => setJustificationModalOpen(false)}
                  disabled={submittingJustification}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    background: 'transparent',
                    color: '#94a3b8',
                    fontSize: '1rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submittingJustification}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(90deg, #3b82f6, #1d4ed8)',
                    color: '#ffffff',
                    fontSize: '1rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)'
                  }}
                >
                  {submittingJustification ? 'Enviando...' : 'Enviar Justificativo'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {selectedCuotaForPayment && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '1rem'
        }}>
          <div style={{
            background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 0.98))',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '16px',
            padding: '2rem',
            width: '100%',
            maxWidth: '480px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4)',
            color: '#f8fafc'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '1.5rem' }}>💳</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#ef4444' }}>webpay<span style={{ color: '#3b82f6' }}>plus</span></h3>
                  <small style={{ color: '#94a3b8', fontSize: '0.7rem' }}>Transacción Segura de Transbank</small>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedCuotaForPayment(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.5rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#94a3b8' }}>
                Comercio: <strong style={{ color: '#f1f5f9' }}>Colegio Kintsugi Academy</strong>
              </p>
              <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#94a3b8' }}>
                Cuota: <strong style={{ color: '#f1f5f9' }}>Cuota #{selectedCuotaForPayment.numero_cuota} ({selectedCuotaForPayment.anio}/{String(selectedCuotaForPayment.mes).padStart(2, '0')})</strong>
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px dashed rgba(255, 255, 255, 0.1)' }}>
                <span style={{ fontSize: '1rem', fontWeight: 600 }}>Monto a pagar:</span>
                <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#10b981' }}>
                  ${formatNumber(selectedCuotaForPayment.saldo_pendiente, '0')}
                </span>
              </div>
            </div>

            <form onSubmit={handleProcessWebpay} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.35rem' }}>Número de Tarjeta</label>
                <input
                  type="text"
                  value={webpayCardNumber}
                  onChange={(e) => setWebpayCardNumber(e.target.value)}
                  required
                  disabled={webpayProcessing}
                  placeholder="xxxx xxxx xxxx xxxx"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    background: 'rgba(15, 23, 42, 0.6)',
                    color: '#f8fafc',
                    fontSize: '1rem'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.35rem' }}>Vencimiento</label>
                  <input
                    type="text"
                    value={webpayExpiry}
                    onChange={(e) => setWebpayExpiry(e.target.value)}
                    required
                    disabled={webpayProcessing}
                    placeholder="MM/AA"
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      background: 'rgba(15, 23, 42, 0.6)',
                      color: '#f8fafc',
                      fontSize: '1rem'
                    }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.35rem' }}>CVV</label>
                  <input
                    type="password"
                    value={webpayCvv}
                    onChange={(e) => setWebpayCvv(e.target.value)}
                    required
                    disabled={webpayProcessing}
                    maxLength={4}
                    placeholder="•••"
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      background: 'rgba(15, 23, 42, 0.6)',
                      color: '#f8fafc',
                      fontSize: '1rem'
                    }}
                  />
                </div>
              </div>

              <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
                <button
                  type="button"
                  onClick={() => setSelectedCuotaForPayment(null)}
                  disabled={webpayProcessing}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    background: 'transparent',
                    color: '#94a3b8',
                    fontSize: '1rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={webpayProcessing}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(90deg, #ef4444, #e11d48)',
                    color: '#ffffff',
                    fontSize: '1rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)',
                    transition: 'all 0.2s'
                  }}
                >
                  {webpayProcessing ? 'Procesando...' : 'Pagar con Webpay'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

