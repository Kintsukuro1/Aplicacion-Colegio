import { useMemo, useEffect, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../services/apiClient';
import { useToast } from '../../components/feedback/Toast';
import { SummarySkeleton } from '../../components/feedback/TableLoadingState';
import { formatNumber, formatGrade, normalizeGrade } from '../../utils/formatters';
import { EmptySection, SectionStatus } from './StudentSelfCommon';

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
  mis_anotaciones: 'student-history',
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
  '/estudiante/perfil': 'student-profile',
  '/estudiante/mis-clases': 'student-classes',
  '/estudiante/mis-notas': 'student-grades',
  '/estudiante/asistencia': 'student-attendance',
  '/estudiante/mi-asistencia': 'student-attendance',
  '/estudiante/historial': 'student-history',
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

  const profileError = profileErrorObj?.message;
  const classesError = classesErrorObj?.message;
  const gradesError = gradesErrorObj?.message;
  const attendanceError = attendanceErrorObj?.message;
  const comunicadosError = comunicadosErrorObj?.message;
  const conversationsError = conversationsErrorObj?.message;
  const messagesError = messagesErrorObj?.message;
  
  const classes = Array.isArray(classesData) ? classesData : [];
  const grades = Array.isArray(gradesData) ? gradesData : [];
  const attendance = Array.isArray(attendanceData) ? attendanceData : [];
  const comunicados = Array.isArray(comunicadosData?.comunicados) ? comunicadosData.comunicados : [];
  const conversaciones = Array.isArray(conversationsData) ? conversationsData : [];
  const mensajes = Array.isArray(messagesData) ? messagesData : [];

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

  const quickLinks = [
    { id: 'student-profile', label: 'Mi Perfil', query: 'perfil' },
    { id: 'student-classes', label: 'Mis Clases', query: 'clases' },
    { id: 'student-grades', label: 'Mis Notas', query: 'notas' },
    { id: 'student-attendance', label: 'Mi Asistencia', query: 'asistencia' },
    { id: 'student-history', label: 'Historial Académico', query: 'historial' },
    { id: 'student-tasks', label: 'Mis Tareas', query: 'tareas' },
    { id: 'student-task-calendar', label: 'Calendario de Tareas', query: 'calendario_tareas' },
    { id: 'student-comunicados', label: 'Comunicados', query: 'comunicados' },
    { id: 'student-messages', label: 'Mensajes', query: 'mensajes' },
    { id: 'student-certificados', label: 'Certificados', query: 'certificados' },
    { id: 'student-estado-cuenta', label: 'Estado de Cuenta', query: 'estado_cuenta' },
    { id: 'student-mis-pagos', label: 'Mis Pagos', query: 'mis_pagos' },
    { id: 'student-dashboard', label: 'Graficos', query: 'dashboard_graficos' },
  ];

  useEffect(() => {
    const tabFromUrl =
      normalizeStudentTab(searchParams.get('tab') || searchParams.get('section') || searchParams.get('pagina')) ||
      STUDENT_PATH_TABS[location.pathname.replace(/\/$/, '')];
    if (tabFromUrl && tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [activeTab, location.pathname, searchParams]);

  function onTabChange(link) {
    setActiveTab(link.id);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('tab', link.query);
    setSearchParams(nextParams, { replace: true });
  }

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

  const studentId = profile?.id || profile?.estudiante_id || profile?.perfil_estudiante?.id;
  const certificateLinks = studentId
    ? [
        { label: 'Certificado de notas', href: `${apiClient.baseUrl}/pdf/certificado-notas/${studentId}/` },
        { label: 'Certificado de matricula', href: `${apiClient.baseUrl}/pdf/certificado-matricula/${studentId}/` },
        { label: 'Informe de rendimiento', href: `${apiClient.baseUrl}/pdf/informe-rendimiento/${studentId}/` },
      ]
    : [];

  const historyAverage = gradeAverage;

  return (
    <section>
      <header className="page-header">
        <div>
          <h2 data-testid="student-self-title">Estudiante: Mi Panel</h2>
          <p>Resumen personal con perfil, clases, notas, asistencia e historial académico.</p>
        </div>
      </header>

      <div className="tabs" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
        {quickLinks.map((link) => (
          <button
            key={link.id}
            type="button"
            className={activeTab === link.id ? 'primary' : 'secondary'}
            onClick={() => onTabChange(link)}
            style={{ whiteSpace: 'nowrap' }}
          >
            {link.label}
          </button>
        ))}
      </div>

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
        {activeTab === 'student-grades' && <StudentGradesTab grades={grades} loading={loadingGrades} error={gradesError} />}
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
        {activeTab === 'student-tasks' && (
          <article className="card section-card">
            <h3>Mis Tareas</h3>
            <EmptySection
              title="Modulo en preparacion"
              description="Las tareas se mostraran aqui cuando el endpoint de tareas este disponible."
            />
            <p style={{ marginTop: '0.75rem', color: 'var(--muted)' }}>
              Si necesitas entregar una tarea, confirma con tu profesor el canal de entrega actual.
            </p>
          </article>
        )}
        {activeTab === 'student-task-calendar' && (
          <article className="card section-card">
            <h3>Calendario de Tareas</h3>
            <EmptySection
              title="Sin eventos cargados"
              description="El calendario de tareas se activara cuando tengamos fechas asociadas a tareas del ciclo."
            />
          </article>
        )}
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
            ) : conversaciones.length === 0 ? (
              <EmptySection title="Sin conversaciones" description="No hay conversaciones activas por ahora." />
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
                {messagesError ? (
                  <div className="error-box" role="alert" aria-live="assertive">{messagesError}</div>
                ) : loadingMessages ? (
                  <SectionStatus title="Cargando mensajes" description="Actualizando conversacion seleccionada." loading />
                ) : mensajes.length === 0 ? (
                  <EmptySection title="Sin mensajes" description="No hay mensajes en esta conversacion." />
                ) : (
                  <ul className="compact-list" style={{ marginTop: '1rem' }}>
                    {mensajes.slice(-15).map((item) => (
                      <li key={item.id_mensaje || item.id}>
                        <strong>{item.emisor_nombre || 'Usuario'}</strong>
                        <p style={{ margin: '0.35rem 0 0' }}>{item.contenido || 'Sin contenido'}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </article>
        )}
        {activeTab === 'student-certificados' && (
          <article className="card section-card">
            <h3>Certificados</h3>
            {certificateLinks.length === 0 ? (
              <EmptySection title="Sin certificados" description="No se pudo identificar el ID del estudiante para generar certificados." />
            ) : (
              <ul className="compact-list">
                {certificateLinks.map((item) => (
                  <li key={item.href}>
                    <a href={item.href} target="_blank" rel="noreferrer">{item.label}</a>
                  </li>
                ))}
              </ul>
            )}
          </article>
        )}
        {activeTab === 'student-estado-cuenta' && (
          <article className="card section-card">
            <h3>Estado de Cuenta</h3>
            <EmptySection
              title="Informacion financiera pendiente"
              description="El estado de cuenta estara disponible cuando el modulo de finanzas se habilite para estudiantes."
            />
          </article>
        )}
        {activeTab === 'student-mis-pagos' && (
          <article className="card section-card">
            <h3>Mis Pagos</h3>
            <EmptySection
              title="Historial en preparacion"
              description="El historial de pagos se publicara cuando el colegio active el modulo de pagos para estudiantes."
            />
          </article>
        )}
        {activeTab === 'student-dashboard' && (
          <article className="card section-card">
            <h3>Graficos del Dashboard</h3>
            <div className="summary-grid">
              {summaryLoading
                ? Array.from({ length: 4 }).map((_, index) => (
                    <SummarySkeleton key={index} />
                  ))
                : profileCards.map((item) => (
                    <article key={item.title} className="summary-tile">
                      <small>{item.title}</small>
                      <strong>{item.value}</strong>
                      <span>{item.subtitle}</span>
                    </article>
                  ))}
            </div>
          </article>
        )}
      </div>
    </section>
  );
}

