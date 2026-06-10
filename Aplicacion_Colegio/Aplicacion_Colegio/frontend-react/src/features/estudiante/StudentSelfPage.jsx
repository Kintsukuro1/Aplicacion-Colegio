import { useMemo, useEffect, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../components/feedback/Toast';
import { SummarySkeleton } from '../../components/feedback/TableLoadingState';
import { formatNumber, formatGrade, normalizeGrade } from '../../utils/formatters';
import { EmptySection, SectionStatus } from './StudentSelfCommon';
import GradesChart from './GradesChart';
import AttendanceChart from './AttendanceChart';

function formatPercentage(value) {
  if (value === null || value === undefined || value === '') {
    return '-';
  }

  return `${formatNumber(value, '-')}%`;
}

function buildAverage(items, valueSelector = (item) => item?.promedio) {
  let total = 0;
  let count = 0;
  for (const item of items) {
    const rawValue = valueSelector(item);
    if (rawValue === null || rawValue === undefined || rawValue === '') {
      continue;
    }

    const value = Number(rawValue);
    if (!Number.isNaN(value)) {
      total += value;
      count += 1;
    }
  }

  if (count === 0) {
    return null;
  }

  return total / count;
}

function resolveError(err, fallback) {
  return err?.payload?.detail || err?.payload?.error || err?.message || fallback;
}



import { StudentProfileTab } from './StudentProfileTab';
import { StudentClassesTab } from './StudentClassesTab';
import { StudentGradesTab } from './StudentGradesTab';
import { StudentAttendanceTab } from './StudentAttendanceTab';
import { StudentHistoryTab } from './StudentHistoryTab';
import { StudentTasksTab } from './StudentTasksTab';
import { StudentTaskCalendarTab } from './StudentTaskCalendarTab';

const STUDENT_TAB_ALIASES = {
  perfil: 'student-profile',
  profile: 'student-profile',
  inicio: 'student-profile',
  student_profile: 'student-profile',
  'student-profile': 'student-profile',
  clases: 'student-classes',
  mis_clases: 'student-classes',
  mi_horario: 'student-classes',
  classes: 'student-classes',
  'student-classes': 'student-classes',
  notas: 'student-grades',
  mis_notas: 'student-grades',
  mis_evaluaciones: 'student-grades',
  grades: 'student-grades',
  'student-grades': 'student-grades',
  asistencia: 'student-attendance',
  mi_asistencia: 'student-attendance',
  attendance: 'student-attendance',
  'student-attendance': 'student-attendance',
  historial: 'student-history',
  mis_anotaciones: 'student-annotations',
  anotaciones: 'student-annotations',
  history: 'student-history',
  'student-history': 'student-history',
  tareas: 'student-tasks',
  mis_tareas: 'student-tasks',
  calendario_tareas: 'student-task-calendar',
  calendario: 'student-task-calendar',
  comunicados: 'student-comunicados',
  mensajes: 'student-messages',
  mis_certificados: 'student-certificados',
  certificados: 'student-certificados',
  estado_cuenta: 'student-estado-cuenta',
  mis_pagos: 'student-mis-pagos',
  dashboard_graficos: 'student-dashboard',
};

const STUDENT_PATH_TABS = {
  '/estudiante/inicio': 'student-profile',
  '/estudiante/perfil': 'student-profile',
  '/estudiante/mis-clases': 'student-classes',
  '/estudiante/mi-horario': 'student-classes',
  '/estudiante/mis-notas': 'student-grades',
  '/estudiante/mis-evaluaciones': 'student-grades',
  '/estudiante/asistencia': 'student-attendance',
  '/estudiante/mi-asistencia': 'student-attendance',
  '/estudiante/historial': 'student-history',
  '/estudiante/mis-anotaciones': 'student-annotations',
  '/estudiante/tareas': 'student-tasks',
  '/estudiante/calendario-tareas': 'student-task-calendar',
  '/estudiante/comunicados': 'student-comunicados',
  '/estudiante/mensajes': 'student-messages',
  '/estudiante/mis-certificados': 'student-certificados',
  '/estudiante/estado-cuenta': 'student-estado-cuenta',
  '/estudiante/mis-pagos': 'student-mis-pagos',
  '/estudiante/dashboard-graficos': 'student-dashboard',
};

function normalizeStudentTab(value) {
  const key = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_');
  return STUDENT_TAB_ALIASES[key] || null;
}

export default function StudentSelfPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab =
    normalizeStudentTab(searchParams.get('tab') || searchParams.get('section') || searchParams.get('pagina')) ||
    STUDENT_PATH_TABS[location.pathname.replace(/\/$/, '')] ||
    'student-profile';
  const [activeTab, setActiveTab] = useState(initialTab);
  const [selectedCycle, setSelectedCycle] = useState('');
  const [selectedConversationId, setSelectedConversationId] = useState('');
  const [confirmingComunicadoId, setConfirmingComunicadoId] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [selectedCuotaForPayment, setSelectedCuotaForPayment] = useState(null);
  const [webpayCardNumber, setWebpayCardNumber] = useState('');
  const [webpayExpiry, setWebpayExpiry] = useState('');
  const [webpayCvv, setWebpayCvv] = useState('');
  const [webpayProcessing, setWebpayProcessing] = useState(false);
  const [isNewChatOpen, setIsNewChatOpen] = useState(false);
  const [newChatClassId, setNewChatClassId] = useState('');
  const [newChatText, setNewChatText] = useState('');
  const [creatingChat, setCreatingChat] = useState(false);

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

  const LOW_GRADE_THRESHOLD = 4;
  const LOW_ATTENDANCE_THRESHOLD = 85;

  const { data: profile, isLoading: loadingProfile, error: profileErrorObj } = useQuery({
    queryKey: ['student-profile'],
    queryFn: () => apiClient.get('/api/v1/estudiante/mi-perfil/')
  });
  const { data: classesData = [], isLoading: loadingClasses, error: classesErrorObj } = useQuery({
    queryKey: ['student-classes'],
    queryFn: () => apiClient.get('/api/v1/estudiante/mis-clases/')
  });
  const { data: gradesData = [], isLoading: loadingGrades, error: gradesErrorObj } = useQuery({
    queryKey: ['student-grades'],
    queryFn: () => apiClient.get('/api/v1/estudiante/mis-notas/')
  });
  const { data: attendanceData = [], isLoading: loadingAttendance, error: attendanceErrorObj } = useQuery({
    queryKey: ['student-attendance'],
    queryFn: () => apiClient.get('/api/v1/estudiante/mi-asistencia/')
  });
  const { data: comunicadosData, isLoading: loadingComunicados, error: comunicadosErrorObj } = useQuery({
    queryKey: ['student-comunicados'],
    queryFn: () => apiClient.get('/api/v1/comunicados/mis-comunicados/'),
    enabled: activeTab === 'student-comunicados'
  });
  const { data: conversationsData, isLoading: loadingConversations, error: conversationsErrorObj } = useQuery({
    queryKey: ['student-conversaciones'],
    queryFn: () => apiClient.get('/api/v1/mensajeria/conversaciones/'),
    enabled: activeTab === 'student-messages'
  });
  const { data: messagesData, isLoading: loadingMessages, error: messagesErrorObj } = useQuery({
    queryKey: ['student-mensajes', selectedConversationId],
    queryFn: () => apiClient.get(`/api/v1/mensajeria/conversaciones/${selectedConversationId}/mensajes/`),
    enabled: activeTab === 'student-messages' && Boolean(selectedConversationId)
  });
  const { data: estadoCuenta, isLoading: loadingEstadoCuenta, error: estadoCuentaErrorObj } = useQuery({
    queryKey: ['student-estado-cuenta'],
    queryFn: () => apiClient.get('/api/v1/estudiante/estado-cuenta/'),
    enabled: activeTab === 'student-estado-cuenta'
  });
  const { data: misPagos, isLoading: loadingMisPagos, error: misPagosErrorObj } = useQuery({
    queryKey: ['student-mis-pagos'],
    queryFn: () => apiClient.get('/api/v1/estudiante/mis-pagos/'),
    enabled: activeTab === 'student-mis-pagos'
  });

  const profileError = profileErrorObj?.message;
  const classesError = classesErrorObj?.message;
  const gradesError = gradesErrorObj?.message;
  const attendanceError = attendanceErrorObj?.message;
  const comunicadosError = comunicadosErrorObj?.message;
  const conversationsError = conversationsErrorObj?.message;
  const messagesError = messagesErrorObj?.message;
  const estadoCuentaError = estadoCuentaErrorObj?.message;
  const misPagosError = misPagosErrorObj?.message;
  
  const classes = Array.isArray(classesData) ? classesData : [];
  const grades = Array.isArray(gradesData) ? gradesData : [];
  const attendance = Array.isArray(attendanceData) ? attendanceData : [];
  const comunicados = Array.isArray(comunicadosData?.comunicados) ? comunicadosData.comunicados : [];
  const conversaciones = Array.isArray(conversationsData) ? conversationsData : [];
  const mensajes = Array.isArray(messagesData) ? messagesData : [];

  const generalGradesChartData = useMemo(() => {
    if (!grades || grades.length === 0) return null;

    const sortedGrades = grades.toSorted((a, b) => {
      const dateA = new Date(a.fecha_evaluacion || a.fecha_creacion || 0);
      const dateB = new Date(b.fecha_evaluacion || b.fecha_creacion || 0);
      return dateA - dateB;
    });

    const labels = sortedGrades.map((g, i) => g.evaluacion_nombre || g.evaluacion || g.nombre || `Nota ${i + 1}`);
    const data = sortedGrades.map((g) => normalizeGrade(g.nota ?? g.promedio));
    const pointColors = data.map((value) => (value !== null && value < 4 ? '#ef4444' : '#2563eb'));

    return {
      labels,
      datasets: [
        {
          label: 'Evolución de Notas',
          data,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.3,
          fill: true,
          pointBackgroundColor: pointColors,
          pointBorderColor: pointColors,
        }
      ]
    };
  }, [grades]);

  const attendanceChartData = useMemo(() => {
    if (!attendance || attendance.length === 0) return null;
    const totalClasses = attendance.length;
    const presentCount = attendance.filter((a) => a.estado === 'P' || a.estado === 'T').length;
    const absentCount = totalClasses - presentCount;

    return {
      labels: ['Presente/Tarde', 'Ausente/Inasistente'],
      datasets: [
        {
          data: [presentCount, absentCount],
          backgroundColor: ['rgba(34, 197, 94, 0.85)', 'rgba(239, 68, 68, 0.85)'],
          borderColor: ['#22c55e', '#ef4444'],
          borderWidth: 1,
        },
      ],
    };
  }, [attendance]);

  const academicAnnotations = useMemo(() => {
    return attendance
      .filter((item) => String(item?.observaciones || '').trim() !== '')
      .map((item) => ({
        id: item.id_asistencia || `${item.clase_id}-${item.fecha}`,
        fecha: item.fecha,
        curso: item.curso_nombre,
        asignatura: item.asignatura_nombre,
        estado: item.estado,
        observaciones: item.observaciones,
      }));
  }, [attendance]);

  const historyUrl = selectedCycle 
    ? `/api/v1/estudiante/historial-academico/?ciclo=${selectedCycle}`
    : '/api/v1/estudiante/historial-academico/';
  const { 
    data: history, 
    isLoading: loadingHistory, 
    error: historyErrorObj 
  } = useQuery({
    queryKey: ['student-history', selectedCycle],
    queryFn: () => apiClient.get(historyUrl)
  });
  const historyError = historyErrorObj?.message;

  // We need an effect to sync selectedCycle based on the loaded history
  useEffect(() => {
    if (!selectedCycle && history?.ciclo?.id) {
      setSelectedCycle(String(history.ciclo.id));
    }
  }, [history, selectedCycle]);

  useEffect(() => {
    if (activeTab !== 'student-messages') return;
    if (!selectedConversationId && conversaciones.length > 0) {
      const firstId = conversaciones[0]?.id_conversacion || conversaciones[0]?.id;
      if (firstId) {
        setSelectedConversationId(String(firstId));
      }
    }
  }, [activeTab, conversaciones, selectedConversationId]);

  const summaryLoading = loadingProfile || loadingClasses || loadingGrades || loadingAttendance || loadingHistory;
  const hasAnyError = profileError || classesError || gradesError || attendanceError || historyError || comunicadosError || conversationsError || messagesError;


  useEffect(() => {
    const tabFromUrl =
      normalizeStudentTab(searchParams.get('tab') || searchParams.get('section') || searchParams.get('pagina')) ||
      STUDENT_PATH_TABS[location.pathname.replace(/\/$/, '')];
    if (tabFromUrl && tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [activeTab, location.pathname, searchParams]);

  function onConversationChange(value) {
    setSelectedConversationId(value);
  }

  async function onConfirmComunicado(comunicadoId) {
    if (!comunicadoId) return;
    setConfirmingComunicadoId(comunicadoId);
    try {
      await apiClient.post(`/api/v1/comunicados/${comunicadoId}/confirmar/`, {});
      toast.success('Comunicado confirmado.');
      await queryClient.invalidateQueries({ queryKey: ['student-comunicados'] });
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
      await queryClient.invalidateQueries({ queryKey: ['student-mensajes', selectedConversationId] });
      await queryClient.invalidateQueries({ queryKey: ['student-conversaciones'] });
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo enviar el mensaje.'));
    } finally {
      setSendingMessage(false);
    }
  }

  async function handleCreateChat(e) {
    e.preventDefault();
    if (!newChatClassId || !newChatText.trim()) return;

    const selectedClass = classes.find(c => String(c.clase_id) === String(newChatClassId));
    if (!selectedClass) {
      toast.error('Clase no válida.');
      return;
    }

    setCreatingChat(true);
    try {
      const conversation = await apiClient.post('/api/v1/mensajeria/conversaciones/', {
        clase_id: Number(newChatClassId),
        destinatario_id: Number(selectedClass.profesor_id),
      });

      const convId = conversation.id_conversacion || conversation.id;

      await apiClient.post(`/api/v1/mensajeria/conversaciones/${convId}/mensajes/`, {
        contenido: newChatText,
      });

      toast.success('Conversación iniciada con éxito.');
      setNewChatClassId('');
      setNewChatText('');
      setIsNewChatOpen(false);

      await queryClient.invalidateQueries({ queryKey: ['student-conversaciones'] });
      setSelectedConversationId(String(convId));
    } catch (err) {
      toast.error(resolveError(err, 'No se pudo iniciar la conversación.'));
    } finally {
      setCreatingChat(false);
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
      await queryClient.invalidateQueries({ queryKey: ['student-estado-cuenta'] });
      await queryClient.invalidateQueries({ queryKey: ['student-mis-pagos'] });
    } catch (err) {
      toast.error(resolveError(err, 'Ocurrió un error al procesar el pago.'));
    } finally {
      setWebpayProcessing(false);
    }
  }

  const gradeAverage = useMemo(
    () => buildAverage(history?.asignaturas || [], (item) => normalizeGrade(item?.promedio)),
    [history]
  );

  const attendanceAverage = useMemo(
    () => buildAverage(history?.asignaturas || [], (item) => item?.porcentaje_asistencia),
    [history]
  );

  const hasLowTest = useMemo(
    () => grades.some((item) => {
      const value = normalizeGrade(item?.nota ?? item?.promedio);
      return value !== null && value < LOW_GRADE_THRESHOLD;
    }),
    [grades]
  );

  const isRepeating = useMemo(() => {
    const lowAverage = gradeAverage !== null && gradeAverage < LOW_GRADE_THRESHOLD;
    const lowAttendance = attendanceAverage !== null && attendanceAverage < LOW_ATTENDANCE_THRESHOLD;
    return lowAverage || lowAttendance;
  }, [attendanceAverage, gradeAverage]);

  const statusBadges = useMemo(() => {
    const badges = [];

    if (profile?.tiene_nee) {
      badges.push({ label: 'NEE', tone: 'warning', description: profile?.tipo_nee || 'Necesidades especiales' });
    }

    if (hasLowTest) {
      badges.push({ label: 'Bajo 4,0', tone: 'danger', description: 'Rendimiento bajo en una evaluacion' });
    }

    if (isRepeating) {
      badges.push({ label: 'Repitencia', tone: 'danger', description: 'Riesgo por notas o asistencia' });
    }

    return badges;
  }, [hasLowTest, isRepeating, profile?.tiene_nee, profile?.tipo_nee]);

  const profileCards = useMemo(() => {
    const subjectCount = classes.length;
    const pendingTasks = Array.isArray(grades)
      ? grades.reduce((acc, item) => acc + (Number(item?.pendientes) || 0), 0)
      : 0;

    return [
      {
        title: 'Mi Curso',
        value: profile?.curso_actual || profile?.curso || 'Sin curso',
        subtitle: profile?.colegio || profile?.escuela || 'Perfil estudiante',
      },
      {
        title: 'Asignaturas',
        value: subjectCount,
        subtitle: subjectCount > 0 ? 'Clases activas en el ciclo' : 'Sin clases registradas',
      },
      {
        title: 'Promedio general',
        value: gradeAverage !== null ? formatGrade(gradeAverage, '-') : '-',
        subtitle: gradeAverage !== null ? 'Promedio ponderado del historial' : 'Aún no hay notas suficientes',
      },
      {
        title: 'Asistencia',
        value: attendanceAverage !== null ? formatPercentage(attendanceAverage) : '-',
        subtitle: attendanceAverage !== null ? 'Promedio del ciclo actual' : 'Sin datos de asistencia',
      },
      {
        title: 'Tareas pendientes',
        value: pendingTasks,
        subtitle: pendingTasks > 0 ? 'Revisa tareas abiertas' : 'Sin tareas pendientes',
      },
    ];
  }, [attendanceAverage, classes.length, gradeAverage, grades, profile]);


  const historyAverage = gradeAverage;

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="student-self-title">Estudiante: Mi Panel</h2>
          <p>Resumen personal con perfil, clases, notas, asistencia e historial académico.</p>
        </div>
      </header>

      <div className="stack">
        {activeTab === 'student-profile' && (
          <StudentProfileTab
            profile={profile}
            loading={loadingProfile}
            error={profileError}
            statusBadges={statusBadges}
          />
        )}
        {activeTab === 'student-classes' && <StudentClassesTab classes={classes} loading={loadingClasses} error={classesError} />}
        {activeTab === 'student-grades' && (
          <StudentGradesTab
            grades={grades}
            loading={loadingGrades}
            error={gradesError}
            classes={classes}
          />
        )}
        {activeTab === 'student-attendance' && <StudentAttendanceTab attendance={attendance} loading={loadingAttendance} error={attendanceError} />}
        {activeTab === 'student-history' && (
          <StudentHistoryTab
            history={history}
            loading={loadingHistory}
            error={historyError}
            selectedCycle={selectedCycle}
            onCycleChange={setSelectedCycle}
            historyAverage={historyAverage}
            formatPercentage={formatPercentage}
          />
        )}
        {activeTab === 'student-annotations' && (
          <article className="card section-card">
            <h3>Mis Anotaciones</h3>
            {loadingAttendance ? (
              <SectionStatus title="Cargando anotaciones" description="Revisando observaciones academicas." loading />
            ) : attendanceError ? (
              <div className="error-box" role="alert" aria-live="assertive">{attendanceError}</div>
            ) : academicAnnotations.length === 0 ? (
              <EmptySection title="Sin anotaciones" description="No hay observaciones academicas registradas." />
            ) : (
              <ul className="compact-list">
                {academicAnnotations.map((item) => (
                  <li key={item.id}>
                    <strong>{item.asignatura || 'Asignatura'}</strong>
                    <span> - {item.curso || 'Curso'}</span>
                    <p style={{ margin: '0.35rem 0' }}>{item.observaciones}</p>
                    <span style={{ color: 'var(--muted)' }}>{item.fecha} {item.estado ? `- ${item.estado}` : ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </article>
        )}
        {activeTab === 'student-tasks' && <StudentTasksTab />}
        {activeTab === 'student-task-calendar' && <StudentTaskCalendarTab />}
        {activeTab === 'student-comunicados' && (
          <article className="card section-card">
            <h3>Comunicados</h3>
            {comunicadosError ? (
              <div className="error-box" role="alert" aria-live="assertive">{comunicadosError}</div>
            ) : loadingComunicados ? (
              <SectionStatus title="Cargando comunicados" description="Sincronizando comunicaciones del colegio." loading />
            ) : comunicados.length === 0 ? (
              <EmptySection title="Sin comunicados" description="No hay comunicados disponibles por ahora." />
            ) : (
              <ul className="compact-list">
                {comunicados.map((item) => {
                  const comunicadoId = item.id || item.id_comunicado;
                  return (
                    <li key={comunicadoId}>
                      <strong>{item.titulo || 'Comunicado'}</strong>
                      <p style={{ margin: '0.5rem 0' }}>{item.contenido || 'Sin detalle disponible.'}</p>
                      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
                        <span style={{ color: 'var(--muted)' }}>{item.fecha_publicacion || item.fecha_evento || 'Sin fecha'}</span>
                        {item.requiere_confirmacion ? (
                          <button
                            type="button"
                            onClick={() => onConfirmComunicado(comunicadoId)}
                            disabled={confirmingComunicadoId === comunicadoId}
                          >
                            {confirmingComunicadoId === comunicadoId ? 'Confirmando...' : item.confirmado ? 'Confirmado' : 'Confirmar lectura'}
                          </button>
                        ) : null}
                        {item.leido ? <span className="badge badge-inactive">Leido</span> : <span className="badge badge-warning">Pendiente</span>}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </article>
        )}
        {activeTab === 'student-messages' && (
          <article className="card section-card">
            <h3>Mensajes</h3>
            {conversationsError ? (
              <div className="error-box" role="alert" aria-live="assertive">{conversationsError}</div>
            ) : loadingConversations ? (
              <SectionStatus title="Cargando conversaciones" description="Buscando mensajes recientes." loading />
            ) : isNewChatOpen ? (
              <form onSubmit={handleCreateChat} className="stack" style={{ gap: '1rem', marginTop: '1rem' }}>
                <h4>Nueva conversación con profesor</h4>
                <label>
                  Asignatura / Profesor
                  <select
                    value={newChatClassId}
                    onChange={(e) => setNewChatClassId(e.target.value)}
                    required
                    style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.2)', background: 'rgba(255, 255, 255, 0.05)', color: 'inherit' }}
                  >
                    <option value="">Seleccionar asignatura...</option>
                    {classes.map((cls) => (
                      <option key={cls.clase_id} value={cls.clase_id}>
                        {cls.asignatura_nombre} - {cls.profesor_nombre}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Mensaje inicial
                  <textarea
                    rows={3}
                    placeholder="Escribe tu mensaje aquí..."
                    value={newChatText}
                    onChange={(e) => setNewChatText(e.target.value)}
                    required
                    style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.2)', background: 'rgba(255, 255, 255, 0.05)', color: 'inherit', resize: 'vertical' }}
                  />
                </label>
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <button type="submit" disabled={creatingChat} className="badge badge-warning" style={{ border: 'none', cursor: 'pointer', padding: '0.5rem 1.25rem' }}>
                    {creatingChat ? 'Iniciando...' : 'Iniciar Conversación'}
                  </button>
                  <button type="button" onClick={() => setIsNewChatOpen(false)} className="badge" style={{ border: '1px solid rgba(148, 163, 184, 0.3)', background: 'transparent', cursor: 'pointer', padding: '0.5rem 1.25rem', color: 'inherit' }}>
                    Cancelar
                  </button>
                </div>
              </form>
            ) : conversaciones.length === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
                <EmptySection title="Sin conversaciones" description="No hay conversaciones activas por ahora." />
                <button
                  type="button"
                  onClick={() => setIsNewChatOpen(true)}
                  className="badge badge-warning"
                  style={{ border: 'none', cursor: 'pointer', padding: '0.75rem 1.5rem', alignSelf: 'center' }}
                >
                  Iniciar Nueva Conversación
                </button>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <label style={{ flex: 1, margin: 0 }}>
                    Conversacion
                    <select value={selectedConversationId} onChange={(event) => onConversationChange(event.target.value)} style={{ width: '100%' }}>
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
                  <button
                    type="button"
                    onClick={() => setIsNewChatOpen(true)}
                    className="badge badge-warning"
                    style={{ border: 'none', cursor: 'pointer', padding: '0.6rem 1rem', marginLeft: '1rem', alignSelf: 'flex-end', height: 'fit-content' }}
                  >
                    Nueva
                  </button>
                </div>
                {messagesError ? (
                  <div className="error-box" role="alert" aria-live="assertive">{messagesError}</div>
                ) : loadingMessages ? (
                  <SectionStatus title="Cargando mensajes" description="Actualizando conversacion seleccionada." loading />
                ) : (
                  <>
                    {mensajes.length === 0 ? (
                      <EmptySection title="Sin mensajes" description="No hay mensajes en esta conversacion." />
                    ) : (
                      <ul className="compact-list" style={{ marginTop: '1rem', maxHeight: '300px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                        {mensajes.slice(-15).map((item) => (
                          <li key={item.id_mensaje || item.id} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginBottom: '0.75rem', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255, 255, 255, 0.02)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <strong style={{ fontSize: '0.9rem', color: 'var(--primary)' }}>{item.emisor_nombre || 'Usuario'}</strong>
                              <small style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>
                                {item.fecha_envio ? new Date(item.fecha_envio).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                              </small>
                            </div>
                            <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--foreground)' }}>{item.contenido || 'Sin contenido'}</p>
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
        )}
        {activeTab === 'student-certificados' && (
          <article className="card section-card">
            <h3>Mis Certificados</h3>
            {loadingProfile ? (
              <SectionStatus title="Cargando certificados" description="Cargando información del estudiante..." loading />
            ) : profileError ? (
              <div className="error-box" role="alert" aria-live="assertive">{profileError}</div>
            ) : !profile?.id ? (
              <EmptySection title="Sin perfil" description="No se pudo cargar la información del estudiante." />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
                <p>Descarga tus certificados institucionales oficiales de manera instantánea:</p>
                <div className="summary-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}>
                  <article className="card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '150px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(148, 163, 184, 0.1)' }}>
                    <div>
                      <h4 style={{ margin: '0 0 0.5rem 0' }}>📄 Certificado de Notas</h4>
                      <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted)' }}>Detalle oficial de las calificaciones obtenidas en el ciclo académico actual.</p>
                    </div>
                    <a
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        handleDownloadPdf(profile.id, 'certificado-notas', `Certificado_Notas_${profile.id}`);
                      }}
                      className="badge badge-warning"
                      style={{ alignSelf: 'flex-start', textDecoration: 'none', marginTop: '1rem', textAlign: 'center', width: 'auto' }}
                    >
                      Descargar PDF
                    </a>
                  </article>
                  <article className="card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '150px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(148, 163, 184, 0.1)' }}>
                    <div>
                      <h4 style={{ margin: '0 0 0.5rem 0' }}>📄 Certificado de Matrícula</h4>
                      <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted)' }}>Documento que acredita la condición de alumno regular matriculado en el establecimiento.</p>
                    </div>
                    <a
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        handleDownloadPdf(profile.id, 'certificado-matricula', `Certificado_Matricula_${profile.id}`);
                      }}
                      className="badge badge-warning"
                      style={{ alignSelf: 'flex-start', textDecoration: 'none', marginTop: '1rem', textAlign: 'center', width: 'auto' }}
                    >
                      Descargar PDF
                    </a>
                  </article>
                  <article className="card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '150px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(148, 163, 184, 0.1)' }}>
                    <div>
                      <h4 style={{ margin: '0 0 0.5rem 0' }}>📄 Informe de Rendimiento</h4>
                      <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted)' }}>Resumen consolidado de rendimiento escolar y porcentajes de asistencia anuales.</p>
                    </div>
                    <a
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        handleDownloadPdf(profile.id, 'informe-rendimiento', `Informe_Rendimiento_${profile.id}`);
                      }}
                      className="badge badge-warning"
                      style={{ alignSelf: 'flex-start', textDecoration: 'none', marginTop: '1rem', textAlign: 'center', width: 'auto' }}
                    >
                      Descargar PDF
                    </a>
                  </article>
                </div>
              </div>
            )}
          </article>
        )}
        {activeTab === 'student-estado-cuenta' && (
          <article className="card section-card">
            <h3>Estado de Cuenta</h3>
            {loadingEstadoCuenta ? (
              <SectionStatus title="Cargando estado de cuenta" description="Consultando saldos y cuotas del ciclo académico actual." loading />
            ) : estadoCuentaError ? (
              <div className="error-box" role="alert" aria-live="assertive">{estadoCuentaError}</div>
            ) : !estadoCuenta?.totales ? (
              <EmptySection title="Sin información" description="No se encontró un estado de cuenta activo para tu matrícula." />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div className="summary-grid">
                  <article className="summary-tile">
                    <small>Total Arancel</small>
                    <strong>${formatNumber(estadoCuenta.totales.total_arancel, '0')}</strong>
                    <span>Monto total del ciclo</span>
                  </article>
                  <article className="summary-tile">
                    <small>Descuentos / Becas</small>
                    <strong>${formatNumber(estadoCuenta.totales.total_descuentos, '0')}</strong>
                    <span>Beneficios aplicados</span>
                  </article>
                  <article className="summary-tile">
                    <small>Total a Pagar</small>
                    <strong>${formatNumber(estadoCuenta.totales.total_a_pagar, '0')}</strong>
                    <span>Monto final neto</span>
                  </article>
                  <article className="summary-tile">
                    <small>Total Pagado</small>
                    <strong>${formatNumber(estadoCuenta.totales.total_pagado, '0')}</strong>
                    <span>Abonos registrados</span>
                  </article>
                  <article className="summary-tile" style={{ background: estadoCuenta.totales.saldo_pendiente > 0 ? 'rgba(239, 68, 68, 0.08)' : undefined }}>
                    <small style={{ color: estadoCuenta.totales.saldo_pendiente > 0 ? '#ef4444' : undefined }}>Saldo Pendiente</small>
                    <strong style={{ color: estadoCuenta.totales.saldo_pendiente > 0 ? '#ef4444' : undefined }}>
                      ${formatNumber(estadoCuenta.totales.saldo_pendiente, '0')}
                    </strong>
                    <span>Saldo por cancelar</span>
                  </article>
                </div>

                <div style={{ marginTop: '0.5rem' }}>
                  <h4 style={{ marginBottom: '1rem' }}>Detalle de Cuotas</h4>
                  {(!estadoCuenta.cuotas || estadoCuenta.cuotas.length === 0) ? (
                    <p style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>No hay cuotas programadas en este ciclo.</p>
                  ) : (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Cuota</th>
                            <th>Año/Mes</th>
                            <th>Monto Original</th>
                            <th>Descuento</th>
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
                                <td>${formatNumber(cuota.monto_original, '0')}</td>
                                <td>${formatNumber(cuota.monto_descuento, '0')}</td>
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
                                      style={{ border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
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
              </div>
            )}
          </article>
        )}
        {activeTab === 'student-mis-pagos' && (
          <article className="card section-card">
            <h3>Historial de Pagos</h3>
            {loadingMisPagos ? (
              <SectionStatus title="Cargando historial de pagos" description="Consultando transacciones y comprobantes registrados." loading />
            ) : misPagosError ? (
              <div className="error-box" role="alert" aria-live="assertive">{misPagosError}</div>
            ) : !misPagos ? (
              <EmptySection title="Sin información" description="No se encontró historial de pagos para tu matrícula." />
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
                    <div style={{ color: 'var(--muted)', fontSize: '0.9rem', padding: '1rem', background: 'rgba(148, 163, 184, 0.03)', borderRadius: '6px', border: '1px dashed rgba(148, 163, 184, 0.15)' }}>
                      Aún no registras abonos o pagos asociados en este ciclo.
                    </div>
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
        )}
        {activeTab === 'student-dashboard' && (
          <article className="card section-card">
            <h3>Gráficos del Dashboard</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem', marginTop: '1.5rem' }}>
              <div className="card" style={{ padding: '1.5rem', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(148, 163, 184, 0.1)' }}>
                <h4 style={{ margin: '0 0 1rem 0', textAlign: 'center' }}>📈 Evolución Académica General</h4>
                {loadingGrades ? (
                  <div style={{ height: '300px', display: 'grid', placeItems: 'center' }}>Cargando notas...</div>
                ) : generalGradesChartData ? (
                  <GradesChart chartData={generalGradesChartData} />
                ) : (
                  <EmptySection title="Sin datos" description="No hay notas registradas para graficar." />
                )}
              </div>

              <div className="card" style={{ padding: '1.5rem', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(148, 163, 184, 0.1)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <h4 style={{ margin: '0 0 1rem 0', textAlign: 'center' }}>📊 Distribución de Asistencia</h4>
                {loadingAttendance ? (
                  <div style={{ height: '300px', display: 'grid', placeItems: 'center' }}>Cargando asistencia...</div>
                ) : attendanceChartData ? (
                  <AttendanceChart chartData={attendanceChartData} totalClasses={attendance.length} />
                ) : (
                  <EmptySection title="Sin datos" description="No hay registros de asistencia para graficar." />
                )}
              </div>
            </div>
          </article>
        )}
      </div>

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

