import { lazy } from 'react';

const DashboardPage = lazy(() => import('../features/dashboard/DashboardPage'));
const TeacherClassesPage = lazy(() => import('../features/profesor/TeacherClassesPage'));
const TeacherAttendancePage = lazy(() => import('../features/profesor/TeacherAttendancePage'));
const TeacherEvaluationsPage = lazy(() => import('../features/profesor/TeacherEvaluationsPage'));
const TeacherGradesPage = lazy(() => import('../features/profesor/TeacherGradesPage'));
const StudentSelfPage = lazy(() => import('../features/estudiante/StudentSelfPage'));
const AdminStudentsPage = lazy(() => import('../features/admin_escolar/AdminStudentsPage'));
const AdminOverviewPage = lazy(() => import('../features/admin_escolar/AdminOverviewPage'));
const AdminCoursesPage = lazy(() => import('../features/admin_escolar/AdminCoursesPage'));
const AdminClassesPage = lazy(() => import('../features/admin_escolar/AdminClassesPage'));
const AdminEvaluationsPage = lazy(() => import('../features/admin_escolar/AdminEvaluationsPage'));
const AdminGradesPage = lazy(() => import('../features/admin_escolar/AdminGradesPage'));
const AdminAttendancePage = lazy(() => import('../features/admin_escolar/AdminAttendancePage'));
const AdminImportExportPage = lazy(() => import('../features/admin_escolar/AdminImportExportPage'));
const CalendarEventsPage = lazy(() => import('../features/calendar/CalendarEventsPage'));
const MeetingRequestsPage = lazy(() => import('../features/reuniones/MeetingRequestsPage'));
const ActiveSessionsPage = lazy(() => import('../features/security/ActiveSessionsPage'));
const PasswordHistoryPage = lazy(() => import('../features/security/PasswordHistoryPage'));
const AsesorFinancieroPage = lazy(() => import('../features/asesor_financiero/AsesorFinancieroPage'));
const InspectorConvivenciaPage = lazy(() => import('../features/inspector_convivencia/InspectorConvivenciaPage'));
const PsicologoOrientadorPage = lazy(() => import('../features/psicologo_orientador/PsicologoOrientadorPage'));
const SoporteTecnicoPage = lazy(() => import('../features/soporte_tecnico/SoporteTecnicoPage'));
const BibliotecarioDigitalPage = lazy(() => import('../features/bibliotecario_digital/BibliotecarioDigitalPage'));
const CoordinadorAcademicoPage = lazy(() => import('../features/coordinador_academico/CoordinadorAcademicoPage'));
const ApoderadoPage = lazy(() => import('../features/apoderado/ApoderadoPage'));
const PricingPage = lazy(() => import('../features/subscriptions/PricingPage'));
const PaymentHistoryPage = lazy(() => import('../features/subscriptions/PaymentHistoryPage'));
const TransferNoticesPage = lazy(() => import('../features/subscriptions/TransferNoticesPage'));

export const APP_ROUTES = [
  {
    path: 'dashboard',
    to: '/dashboard',
    label: 'Inicio',
    component: DashboardPage,
    anyOf: ['DASHBOARD_VIEW_SELF', 'DASHBOARD_VIEW_SCHOOL', 'DASHBOARD_VIEW_ANALYTICS'],
  },
  {
    path: 'admin-escolar/panel',
    to: '/admin-escolar/panel',
    label: 'Panel administrativo',
    component: AdminOverviewPage,
    allowedRoles: ['admin_escolar', 'admin_general'],
    anyOf: ['DASHBOARD_VIEW_SCHOOL', 'DASHBOARD_VIEW_ANALYTICS'],
  },
  {
    path: 'admin-escolar/estudiantes',
    to: '/admin-escolar/estudiantes',
    label: 'Estudiantes',
    component: AdminStudentsPage,
    allowedRoles: ['admin_escolar', 'admin_general'],
    anyOf: ['STUDENT_EDIT', 'STUDENT_CREATE', 'SYSTEM_CONFIGURE'],
    allOf: ['DASHBOARD_VIEW_SCHOOL'],
  },
  {
    path: 'admin-escolar/cursos',
    to: '/admin-escolar/cursos',
    label: 'Cursos',
    component: AdminCoursesPage,
    allowedRoles: ['admin_escolar', 'admin_general'],
    anyOf: ['COURSE_EDIT', 'COURSE_CREATE', 'SYSTEM_CONFIGURE'],
    allOf: ['DASHBOARD_VIEW_SCHOOL'],
  },
  {
    path: 'admin-escolar/clases',
    to: '/admin-escolar/clases',
    label: 'Clases',
    component: AdminClassesPage,
    allowedRoles: ['admin_escolar', 'admin_general'],
    anyOf: ['CLASS_EDIT', 'CLASS_CREATE', 'SYSTEM_CONFIGURE'],
    allOf: ['DASHBOARD_VIEW_SCHOOL'],
  },
  {
    path: 'admin-escolar/evaluaciones',
    to: '/admin-escolar/evaluaciones',
    label: 'Evaluaciones',
    component: AdminEvaluationsPage,
    allowedRoles: ['admin_escolar', 'admin_general'],
    anyOf: ['GRADE_EDIT', 'GRADE_CREATE', 'SYSTEM_CONFIGURE'],
    allOf: ['DASHBOARD_VIEW_SCHOOL'],
  },
  {
    path: 'admin-escolar/calificaciones',
    to: '/admin-escolar/calificaciones',
    label: 'Calificaciones',
    component: AdminGradesPage,
    allowedRoles: ['admin_escolar', 'admin_general'],
    anyOf: ['GRADE_EDIT', 'GRADE_CREATE', 'SYSTEM_CONFIGURE'],
    allOf: ['DASHBOARD_VIEW_SCHOOL'],
  },
  {
    path: 'admin-escolar/asistencias',
    to: '/admin-escolar/asistencias',
    label: 'Asistencias',
    component: AdminAttendancePage,
    allowedRoles: ['admin_escolar', 'admin_general'],
    anyOf: ['CLASS_TAKE_ATTENDANCE', 'SYSTEM_CONFIGURE'],
    allOf: ['DASHBOARD_VIEW_SCHOOL'],
  },
  {
    path: 'admin-escolar/importacion-exportacion',
    to: '/admin-escolar/importacion-exportacion',
    label: 'Importar y exportar',
    component: AdminImportExportPage,
    allowedRoles: ['admin_escolar', 'admin_general'],
    anyOf: ['SYSTEM_ADMIN', 'SYSTEM_CONFIGURE'],
    allOf: ['DASHBOARD_VIEW_SCHOOL'],
  },
  {
    path: 'calendario/eventos',
    to: '/calendario/eventos',
    label: 'Calendario escolar',
    component: CalendarEventsPage,
    anyOf: ['ANNOUNCEMENT_VIEW', 'ANNOUNCEMENT_CREATE', 'ANNOUNCEMENT_EDIT', 'ANNOUNCEMENT_DELETE', 'SYSTEM_ADMIN'],
  },
  {
    path: 'reuniones/solicitudes',
    to: '/reuniones/solicitudes',
    label: 'Solicitudes',
    component: MeetingRequestsPage,
    allowedRoles: ['profesor', 'apoderado', 'admin_escolar', 'admin_general'],
    anyOf: ['CLASS_VIEW', 'SYSTEM_CONFIGURE', 'SYSTEM_ADMIN'],
  },
  {
    path: 'seguridad/sesiones-activas',
    to: '/seguridad/sesiones-activas',
    label: 'Sesiones activas',
    component: ActiveSessionsPage,
    anyOf: ['AUDIT_VIEW', 'SYSTEM_ADMIN'],
  },
  {
    path: 'seguridad/password-history',
    to: '/seguridad/password-history',
    label: 'Historial de claves',
    component: PasswordHistoryPage,
    anyOf: ['AUDIT_VIEW', 'SYSTEM_ADMIN'],
  },
  {
    path: 'profesor/clases',
    to: '/profesor/clases',
    label: 'Mis clases',
    component: TeacherClassesPage,
    allowedRoles: ['profesor'],
    anyOf: ['CLASS_VIEW'],
  },
  {
    path: 'profesor/asistencias',
    to: '/profesor/asistencias',
    label: 'Asistencias',
    component: TeacherAttendancePage,
    allowedRoles: ['profesor'],
    anyOf: ['CLASS_VIEW_ATTENDANCE', 'CLASS_TAKE_ATTENDANCE'],
  },
  {
    path: 'profesor/evaluaciones',
    to: '/profesor/evaluaciones',
    label: 'Evaluaciones',
    component: TeacherEvaluationsPage,
    allowedRoles: ['profesor'],
    anyOf: ['GRADE_VIEW', 'GRADE_CREATE', 'GRADE_EDIT', 'GRADE_DELETE'],
  },
  {
    path: 'profesor/calificaciones',
    to: '/profesor/calificaciones',
    label: 'Calificaciones',
    component: TeacherGradesPage,
    allowedRoles: ['profesor'],
    anyOf: ['GRADE_VIEW', 'GRADE_CREATE', 'GRADE_EDIT', 'GRADE_DELETE'],
  },
  {
    path: 'estudiante/panel',
    to: '/estudiante/panel',
    label: 'Mi panel',
    component: StudentSelfPage,
    allowedRoles: ['estudiante', 'alumno'],
    anyOf: ['PORTAL_ESTUDIANTE'],
  },
  {
    path: 'asesor-financiero/panel',
    to: '/asesor-financiero/panel',
    label: 'Panel financiero',
    component: AsesorFinancieroPage,
    allowedRoles: ['asesor_financiero'],
    anyOf: ['FINANCE_VIEW', 'FINANCE_MANAGE_PAYMENTS'],
  },
  {
    path: 'inspector-convivencia/panel',
    to: '/inspector-convivencia/panel',
    label: 'Panel convivencia',
    component: InspectorConvivenciaPage,
    allowedRoles: ['inspector_convivencia'],
    anyOf: ['DISCIPLINE_VIEW', 'DISCIPLINE_CREATE', 'JUSTIFICATION_APPROVE'],
  },
  {
    path: 'psicologo-orientador/panel',
    to: '/psicologo-orientador/panel',
    label: 'Panel orientacion',
    component: PsicologoOrientadorPage,
    allowedRoles: ['psicologo_orientador'],
    anyOf: ['COUNSELING_VIEW', 'COUNSELING_CREATE', 'REFERRAL_CREATE', 'REFERRAL_EDIT'],
  },
  {
    path: 'soporte-tecnico/panel',
    to: '/soporte-tecnico/panel',
    label: 'Panel soporte',
    component: SoporteTecnicoPage,
    allowedRoles: ['soporte_tecnico_escolar'],
    anyOf: ['SUPPORT_VIEW_TICKETS', 'SUPPORT_CREATE_TICKET', 'SUPPORT_RESOLVE_TICKET', 'SUPPORT_RESET_PASSWORD'],
  },
  {
    path: 'bibliotecario-digital/panel',
    to: '/bibliotecario-digital/panel',
    label: 'Panel biblioteca',
    component: BibliotecarioDigitalPage,
    allowedRoles: ['bibliotecario_digital'],
    anyOf: ['LIBRARY_VIEW', 'LIBRARY_CREATE', 'LIBRARY_MANAGE_LOANS'],
  },
  {
    path: 'coordinador-academico/panel',
    to: '/coordinador-academico/panel',
    label: 'Panel academico',
    component: CoordinadorAcademicoPage,
    allowedRoles: ['coordinador_academico'],
    anyOf: ['PLANNING_VIEW', 'PLANNING_APPROVE'],
  },
  {
    path: 'apoderado/panel',
    to: '/apoderado/panel',
    label: 'Mi panel',
    component: ApoderadoPage,
    allowedRoles: ['apoderado'],
    anyOf: ['PORTAL_APODERADO'],
  },
  {
    path: 'planes',
    to: '/planes',
    label: 'Planes',
    component: PricingPage,
    anyOf: ['FINANCE_MANAGE_PAYMENTS', 'SYSTEM_ADMIN'],
  },
  {
    path: 'pagos/historial',
    to: '/pagos/historial',
    label: 'Historial de pagos',
    component: PaymentHistoryPage,
    anyOf: ['FINANCE_MANAGE_PAYMENTS', 'SYSTEM_ADMIN'],
  },
  {
    path: 'pagos/transferencias',
    to: '/pagos/transferencias',
    label: 'Transferencias',
    component: TransferNoticesPage,
    anyOf: ['FINANCE_MANAGE_PAYMENTS', 'SYSTEM_ADMIN'],
  },
];