from django.urls import path
from django.urls import include
from rest_framework.routers import DefaultRouter

from backend.apps.api.auth import (
    AuditedTokenRefreshView,
    AuditedTokenVerifyView,
    ColegioTokenObtainPairView,
    LogoutView,
)
from backend.apps.api.upload_views import upload_image
from backend.apps.api.apoderado_views import (
    apoderado_comunicados,
    apoderado_justificativos,
    apoderado_mis_pupilos,
    apoderado_pagos_estado,
    apoderado_pupilo_anotaciones,
    apoderado_pupilo_asistencia,
    apoderado_pupilo_notas,
    apoderado_listar_firmas,
    apoderado_firmar_documento,
    apoderado_opciones_admision,
)
from backend.apps.api.pdf_views import (
    api_descargar_certificado_matricula,
    api_descargar_certificado_notas,
    api_descargar_informe_rendimiento,
)
from backend.apps.api.domain_views import (
    AnotacionConvivenciaViewSet,
    ComunicadoViewSet,
    ConversacionViewSet,
    DerivacionExternaViewSet,
    EntrevistaOrientacionViewSet,
    EstadoCuentaViewSet,
    JustificativoInasistenciaViewSet,
    PagoHistorialViewSet,
)
from backend.apps.api.notifications_views import (
    device_deactivate,
    device_register,
    notifications_list,
    notifications_mark_all_read,
    notifications_mark_read,
    notifications_summary,
    notifications_sse_stream,
)
from backend.apps.api.resources_views import (
    ApoderadoViewSet,
    AsignaturaViewSet,
    CicloAcademicoViewSet,
    CursoViewSet,
    MatriculaViewSet,
    StudentViewSet,
    ActividadResolubleViewSet,
    TeacherAttendanceViewSet,
    TeacherClassViewSet,
    TeacherEvaluationViewSet,
    TeacherGradeViewSet,
    dashboard_executive,
    dashboard_schools,
    dashboard_summary,
    ministerial_monthly_report,
    student_my_attendance,
    student_my_classes,
    student_my_grades,
    student_my_profile,
    student_my_tasks,
    student_estado_cuenta,
    student_mis_pagos,
    student_crear_pago,
)
from backend.apps.api.profile_views import my_profile, change_password
from backend.apps.api.views import api_health, me, operational_metrics
from backend.apps.api.tenant_views import tenant_config, tenant_info
from backend.apps.core.views.coordinador_academico.api import (
    actualizar_estado_planificacion as legacy_coordinador_actualizar_planificacion,
    listar_planificaciones as legacy_coordinador_listar_planificaciones,
)
from backend.apps.core.views.estudiante.api import (
    entregar_tarea as legacy_estudiante_entregar_tarea,
)
from backend.apps.core.views.soporte_tecnico.api import (
    actualizar_ticket as legacy_soporte_actualizar_ticket,
    crear_ticket as legacy_soporte_crear_ticket,
    reset_password as legacy_soporte_reset_password,
)
from backend.apps.core.views.inspector_convivencia.api import (
    actualizar_justificativo as legacy_inspector_actualizar_justificativo,
    crear_anotacion as legacy_inspector_crear_anotacion,
    listar_estudiantes as legacy_inspector_listar_estudiantes,
    listar_justificativos as legacy_inspector_listar_justificativos,
    registrar_atraso as legacy_inspector_registrar_atraso,
)
from backend.apps.core.views.psicologo_orientador.api import (
    actualizar_derivacion as legacy_psicologo_actualizar_derivacion,
    crear_derivacion as legacy_psicologo_crear_derivacion,
    crear_entrevista as legacy_psicologo_crear_entrevista,
    listar_estudiantes as legacy_psicologo_listar_estudiantes,
    toggle_pie_status as legacy_psicologo_toggle_pie,
)
from backend.apps.core.views.bibliotecario_digital.api import (
    crear_prestamo as legacy_bibliotecario_crear_prestamo,
    crear_recurso as legacy_bibliotecario_crear_recurso,
    listar_prestamos as legacy_bibliotecario_listar_prestamos,
    listar_recursos as legacy_bibliotecario_listar_recursos,
    listar_usuarios as legacy_bibliotecario_listar_usuarios,
    registrar_devolucion as legacy_bibliotecario_registrar_devolucion,
    toggle_publicar_recurso as legacy_bibliotecario_toggle_publicar_recurso,
)
from backend.apps.core.views.asesor_financiero.pagos_api import (
    listar_pagos as legacy_asesor_financiero_listar_pagos,
)
from backend.apps.api.gestion_escolar_views import (
    FirmaDigitalViewSet,
    MaterialClaseViewSet,
    TeacherAdminViewSet,
    apoderado_pupilo_materiales,
    student_academic_history,
    teacher_my_schedule,
    demo_panel,
)
from backend.apps.api.comunicacion_analitica_views import (
    EventoCalendarioViewSet,
    comunicado_estadisticas,
    confirmar_comunicado,
    mis_comunicados,
    teacher_trends_report,
)
from backend.apps.api.admin_context_views import admin_active_school_context
from backend.apps.api.seguridad_views import (
    active_sessions_list,
    change_password_secure,
    my_sessions,
    password_history_list,
    password_history_export_csv,
    password_history_force_change,
    revoke_all_other_sessions,
    revoke_session,
    security_dashboard,
    sensitive_data_audit_log,
    unblock_ip,
)
from backend.apps.api.finanzas_reuniones_views import (
    cancelar_reunion,
    ciclo_statistics,
    ciclo_transition,
    financial_dashboard,
    financial_morosos_report,
    mis_reuniones,
    reuniones_apoderados_pupilos,
    reuniones_profesores_catalogo,
    responder_reunion,
    solicitar_reunion,
)
from backend.apps.api.importacion_exportacion_views import (
    api_descargar_plantilla,
    api_exportar_asistencia,
    api_exportar_estudiantes,
    api_exportar_profesores,
    api_exportar_reporte_academico,
    api_importacion_dashboard,
    api_importar_datos,
)
from backend.apps.api.payment_views import (
    create_checkout,
    approve_transfer_notice,
    transfer_notices,
    transfer_notices_export,
    payment_history,
    payment_providers,
    notify_transfer,
    payment_webhook,
    plans_list,
    upgrade_subscription,
    cancel_subscription,
    renew_subscription,
)
from backend.apps.api.onboarding_views import (
    onboarding_check_slug,
    onboarding_generate_demo,
    onboarding_register,
)

app_name = 'api'

router = DefaultRouter()
router.register(r'estudiantes', StudentViewSet, basename='api-estudiantes')
router.register(r'cursos', CursoViewSet, basename='api-cursos')
router.register(r'asignaturas', AsignaturaViewSet, basename='api-asignaturas')
router.register(r'ciclos-academicos', CicloAcademicoViewSet, basename='api-ciclos-academicos')
router.register(r'matriculas', MatriculaViewSet, basename='api-matriculas')
router.register(r'apoderados', ApoderadoViewSet, basename='api-apoderados')
router.register(r'profesor/clases', TeacherClassViewSet, basename='api-profesor-clases')
router.register(r'profesor/asistencias', TeacherAttendanceViewSet, basename='api-profesor-asistencias')
router.register(r'profesor/evaluaciones', TeacherEvaluationViewSet, basename='api-profesor-evaluaciones')
router.register(r'profesor/calificaciones', TeacherGradeViewSet, basename='api-profesor-calificaciones')
router.register(r'actividades-resolubles', ActividadResolubleViewSet, basename='api-actividades-resolubles')
# ── Semana 3-4 ──
router.register(r'profesores', TeacherAdminViewSet, basename='api-profesores-admin')
router.register(r'firmas', FirmaDigitalViewSet, basename='api-firmas')
router.register(r'materiales', MaterialClaseViewSet, basename='api-materiales')
# ── Semana 5-6 ──
router.register(r'calendario', EventoCalendarioViewSet, basename='api-calendario')
router.register(r'comunicados', ComunicadoViewSet, basename='api-comunicados')
router.register(r'mensajeria/conversaciones', ConversacionViewSet, basename='api-mensajeria-conversaciones')
router.register(r'convivencia/anotaciones', AnotacionConvivenciaViewSet, basename='api-convivencia-anotaciones')
router.register(r'orientacion/entrevistas', EntrevistaOrientacionViewSet, basename='api-orientacion-entrevistas')
router.register(r'orientacion/derivaciones', DerivacionExternaViewSet, basename='api-orientacion-derivaciones')
router.register(r'justificativos', JustificativoInasistenciaViewSet, basename='api-justificativos')
router.register(r'finanzas/pagos', PagoHistorialViewSet, basename='api-finanzas-pagos')
router.register(r'finanzas/estados-cuenta', EstadoCuentaViewSet, basename='api-finanzas-estados-cuenta')

urlpatterns = [
    path('health/', api_health, name='health'),
    path('tenant/info/', tenant_info, name='tenant_info'),
    path('tenant/config/', tenant_config, name='tenant_config'),
    path('plans/', plans_list, name='plans_list'),
    path('payments/create-checkout/', create_checkout, name='create_checkout'),
    path('payments/webhook/', payment_webhook, name='payment_webhook'),
    path('payments/notify-transfer/', notify_transfer, name='notify_transfer'),
    path('payments/transfer-notices/', transfer_notices, name='transfer_notices'),
    path('payments/transfer-notices/export/', transfer_notices_export, name='transfer_notices_export'),
    path('payments/transfer-notices/approve/', approve_transfer_notice, name='approve_transfer_notice'),
    path('payments/history/', payment_history, name='payment_history'),
    path('payments/providers/', payment_providers, name='payment_providers'),
    path('subscriptions/upgrade/', upgrade_subscription, name='upgrade_subscription'),
    path('subscriptions/cancel/', cancel_subscription, name='cancel_subscription'),
    path('subscriptions/renew/', renew_subscription, name='renew_subscription'),
    path('onboarding/register/', onboarding_register, name='onboarding_register'),
    path('onboarding/check-slug/', onboarding_check_slug, name='onboarding_check_slug'),
    path('onboarding/generate-demo/', onboarding_generate_demo, name='onboarding_generate_demo'),
    path('ops/metrics/', operational_metrics, name='operational_metrics'),
    path('me/', me, name='me_root'),
    path('auth/token/', ColegioTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', AuditedTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', AuditedTokenVerifyView.as_view(), name='token_verify'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', me, name='me'),
    path('notificaciones/', notifications_list, name='notifications_list'),
    path('notificaciones/resumen/', notifications_summary, name='notifications_summary'),
    path('notificaciones/marcar-todas-leidas/', notifications_mark_all_read, name='notifications_mark_all_read'),
    path('notificaciones/<int:notification_id>/marcar-leida/', notifications_mark_read, name='notifications_mark_read'),
    path('notificaciones/dispositivos/registrar/', device_register, name='notifications_device_register'),
    path('notificaciones/dispositivos/<int:device_id>/desactivar/', device_deactivate, name='notifications_device_deactivate'),
    path('notificaciones/stream/', notifications_sse_stream, name='notifications_sse_stream'),
    path('dashboard/resumen/', dashboard_summary, name='dashboard_summary'),
    path('dashboard/executive/', dashboard_executive, name='dashboard_executive'),
    path('dashboard/colegios/', dashboard_schools, name='dashboard_schools'),
    path(
        'reportes/ministeriales/resumen-mensual/',
        ministerial_monthly_report,
        name='ministerial_monthly_report',
    ),
    path('uploads/image/', upload_image, name='upload_image'),
    path('estudiante/mi-perfil/', student_my_profile, name='student_my_profile'),
    path('estudiante/mis-clases/', student_my_classes, name='student_my_classes'),
    path('estudiante/mis-notas/', student_my_grades, name='student_my_grades'),
    path('estudiante/mi-asistencia/', student_my_attendance, name='student_my_attendance'),
    path('estudiante/tareas/', student_my_tasks, name='student_my_tasks'),
    path('estudiante/estado-cuenta/', student_estado_cuenta, name='student_estado_cuenta'),
    path('estudiante/mis-pagos/', student_mis_pagos, name='student_mis_pagos'),
    path('estudiante/pagos/crear/', student_crear_pago, name='student_crear_pago'),
    # ── Self-service profile (todos los roles) ──
    path('perfil/mi-perfil/', my_profile, name='my_profile'),
    path('perfil/cambiar-password/', change_password, name='change_password'),
    path('estudiante/tareas/entregar/', legacy_estudiante_entregar_tarea, name='legacy_estudiante_entregar_tarea'),
    path('apoderado/mis-pupilos/', apoderado_mis_pupilos, name='apoderado_mis_pupilos'),
    path('apoderado/pupilo/<int:student_id>/notas/', apoderado_pupilo_notas, name='apoderado_pupilo_notas'),
    path('apoderado/pupilo/<int:student_id>/asistencia/', apoderado_pupilo_asistencia, name='apoderado_pupilo_asistencia'),
    path('apoderado/pupilo/<int:student_id>/anotaciones/', apoderado_pupilo_anotaciones, name='apoderado_pupilo_anotaciones'),
    path('apoderado/justificativos/', apoderado_justificativos, name='apoderado_justificativos'),
    path('apoderado/firmas/', apoderado_listar_firmas, name='apoderado_listar_firmas'),
    path('apoderado/firmas/firmar/', apoderado_firmar_documento, name='apoderado_firmar_documento'),
    path('apoderado/admision/opciones/', apoderado_opciones_admision, name='apoderado_opciones_admision'),
    path('pdf/certificado-notas/<int:estudiante_id>/', api_descargar_certificado_notas, name='api_descargar_certificado_notas'),
    path('pdf/certificado-matricula/<int:estudiante_id>/', api_descargar_certificado_matricula, name='api_descargar_certificado_matricula'),
    path('pdf/informe-rendimiento/<int:estudiante_id>/', api_descargar_informe_rendimiento, name='api_descargar_informe_rendimiento'),
    path('apoderado/comunicados/', apoderado_comunicados, name='apoderado_comunicados'),
    path('apoderado/pagos/estado/', apoderado_pagos_estado, name='apoderado_pagos_estado'),
    path('apoderado/pupilo/<int:student_id>/materiales/', apoderado_pupilo_materiales, name='apoderado_pupilo_materiales'),
    # ── Semana 3-4: Horario, Historial ──
    path('profesor/mi-horario/', teacher_my_schedule, name='teacher_my_schedule'),
    path('estudiante/historial-academico/', student_academic_history, name='student_academic_history'),
    path('demo/panel/', demo_panel, name='demo_panel'),
    # ── Semana 5-6: Comunicados, Tendencias, Calendario ──
    path('comunicados/<int:comunicado_id>/confirmar/', confirmar_comunicado, name='confirmar_comunicado'),
    path('comunicados/<int:comunicado_id>/estadisticas/', comunicado_estadisticas, name='comunicado_estadisticas'),
    path('comunicados/mis-comunicados/', mis_comunicados, name='mis_comunicados'),
    path('profesor/tendencias/', teacher_trends_report, name='teacher_trends_report'),
    # ── Semana 7-8: Seguridad ──
    path('seguridad/dashboard/', security_dashboard, name='security_dashboard'),
    path('seguridad/mis-sesiones/', my_sessions, name='my_sessions'),
    path('seguridad/sesiones-activas/', active_sessions_list, name='active_sessions_list'),
    path('seguridad/sesiones/<int:session_id>/revocar/', revoke_session, name='revoke_session'),
    path('seguridad/sesiones/revocar-otras/', revoke_all_other_sessions, name='revoke_all_other_sessions'),
    path('seguridad/password-history/', password_history_list, name='password_history_list'),
    path('seguridad/password-history/export/', password_history_export_csv, name='password_history_export_csv'),
    path('seguridad/password-history/forzar-cambio/', password_history_force_change, name='password_history_force_change'),
    path('seguridad/auditoria-datos-sensibles/', sensitive_data_audit_log, name='sensitive_data_audit_log'),
    path('seguridad/desbloquear-ip/', unblock_ip, name='unblock_ip'),
    path('seguridad/cambiar-password/', change_password_secure, name='change_password_secure'),
    path('admin/contexto-colegio/', admin_active_school_context, name='admin_active_school_context'),
    # ── Semana 9-10: Finanzas, Reuniones, Ciclos ──
    path('finanzas/dashboard/', financial_dashboard, name='financial_dashboard'),
    path('finanzas/morosos/', financial_morosos_report, name='financial_morosos_report'),
    path('reuniones/solicitar/', solicitar_reunion, name='solicitar_reunion'),
    path('reuniones/apoderados-pupilos/', reuniones_apoderados_pupilos, name='reuniones_apoderados_pupilos'),
    path('reuniones/profesores/', reuniones_profesores_catalogo, name='reuniones_profesores_catalogo'),
    path('reuniones/mis-reuniones/', mis_reuniones, name='mis_reuniones'),
    path('reuniones/<int:reunion_id>/responder/', responder_reunion, name='responder_reunion'),
    path('reuniones/<int:reunion_id>/cancelar/', cancelar_reunion, name='cancelar_reunion'),
    path('ciclos-academicos/<int:ciclo_id>/transicion/', ciclo_transition, name='ciclo_transition'),
    path('ciclos-academicos/<int:ciclo_id>/estadisticas/', ciclo_statistics, name='ciclo_statistics'),
    # ── Semana 11-12: Importación y Exportación ──
    path('importacion/importar/', api_importar_datos, name='api_importar_datos'),
    path('importacion/plantilla/<str:tipo>/', api_descargar_plantilla, name='api_descargar_plantilla'),
    path('importacion/dashboard/', api_importacion_dashboard, name='api_importacion_dashboard'),
    path('exportacion/estudiantes/', api_exportar_estudiantes, name='api_exportar_estudiantes'),
    path('exportacion/profesores/', api_exportar_profesores, name='api_exportar_profesores'),
    path('exportacion/reporte-academico/', api_exportar_reporte_academico, name='api_exportar_reporte_academico'),
    path('exportacion/asistencia/', api_exportar_asistencia, name='api_exportar_asistencia'),
    path('coordinador/planificaciones/', legacy_coordinador_listar_planificaciones, name='legacy_coordinador_listar_planificaciones'),
    path(
        'coordinador/planificaciones/<int:planificacion_id>/estado/',
        legacy_coordinador_actualizar_planificacion,
        name='legacy_coordinador_actualizar_planificacion',
    ),
    path('soporte/tickets/crear/', legacy_soporte_crear_ticket, name='legacy_soporte_crear_ticket'),
    path('asesor-financiero/pagos/', legacy_asesor_financiero_listar_pagos, name='legacy_asesor_financiero_listar_pagos'),
    path(
        'soporte/tickets/<int:ticket_id>/estado/',
        legacy_soporte_actualizar_ticket,
        name='legacy_soporte_actualizar_ticket',
    ),
    path(
        'soporte/tickets/<int:ticket_id>/actualizar/',
        legacy_soporte_actualizar_ticket,
        name='legacy_soporte_actualizar_ticket_alias_actualizar',
    ),
    path(
        'soporte/usuarios/<int:user_id>/reset_password/',
        legacy_soporte_reset_password,
        name='legacy_soporte_reset_password',
    ),
    path(
        'soporte/usuarios/<int:user_id>/reset-password/',
        legacy_soporte_reset_password,
        name='legacy_soporte_reset_password_alias_hyphen',
    ),
    path('inspector/estudiantes/', legacy_inspector_listar_estudiantes, name='legacy_inspector_listar_estudiantes'),
    path('inspector/justificativos/', legacy_inspector_listar_justificativos, name='legacy_inspector_listar_justificativos'),
    path('inspector/anotaciones/crear/', legacy_inspector_crear_anotacion, name='legacy_inspector_crear_anotacion'),
    path(
        'inspector/justificativos/<int:justificativo_id>/estado/',
        legacy_inspector_actualizar_justificativo,
        name='legacy_inspector_actualizar_justificativo',
    ),
    path(
        'inspector/justificativos/<int:justificativo_id>/revisar/',
        legacy_inspector_actualizar_justificativo,
        name='legacy_inspector_actualizar_justificativo_alias_revisar',
    ),
    path(
        'inspector/asistencia/registrar_atraso/',
        legacy_inspector_registrar_atraso,
        name='legacy_inspector_registrar_atraso',
    ),
    path(
        'inspector/atrasos/registrar/',
        legacy_inspector_registrar_atraso,
        name='legacy_inspector_registrar_atraso_alias_atrasos',
    ),
    path('psicologo/estudiantes/', legacy_psicologo_listar_estudiantes, name='legacy_psicologo_listar_estudiantes'),
    path('psicologo/entrevistas/crear/', legacy_psicologo_crear_entrevista, name='legacy_psicologo_crear_entrevista'),
    path('psicologo/derivaciones/crear/', legacy_psicologo_crear_derivacion, name='legacy_psicologo_crear_derivacion'),
    path(
        'psicologo/derivaciones/<int:derivacion_id>/',
        legacy_psicologo_actualizar_derivacion,
        name='legacy_psicologo_actualizar_derivacion',
    ),
    path(
        'psicologo/derivaciones/<int:derivacion_id>/actualizar/',
        legacy_psicologo_actualizar_derivacion,
        name='legacy_psicologo_actualizar_derivacion_alias_actualizar',
    ),
    path(
        'psicologo/estudiantes/<int:estudiante_id>/pie/',
        legacy_psicologo_toggle_pie,
        name='legacy_psicologo_toggle_pie',
    ),
    path('bibliotecario/recursos/', legacy_bibliotecario_listar_recursos, name='legacy_bibliotecario_listar_recursos'),
    path('bibliotecario/usuarios/', legacy_bibliotecario_listar_usuarios, name='legacy_bibliotecario_listar_usuarios'),
    path('bibliotecario/prestamos/', legacy_bibliotecario_listar_prestamos, name='legacy_bibliotecario_listar_prestamos'),
    path('bibliotecario/recursos/crear/', legacy_bibliotecario_crear_recurso, name='legacy_bibliotecario_crear_recurso'),
    path(
        'bibliotecario/recursos/<int:recurso_id>/publicar/',
        legacy_bibliotecario_toggle_publicar_recurso,
        name='legacy_bibliotecario_toggle_publicar_recurso',
    ),
    path('bibliotecario/prestamos/crear/', legacy_bibliotecario_crear_prestamo, name='legacy_bibliotecario_crear_prestamo'),
    path(
        'bibliotecario/prestamos/<int:prestamo_id>/devolver/',
        legacy_bibliotecario_registrar_devolucion,
        name='legacy_bibliotecario_registrar_devolucion',
    ),
    path(
        'bibliotecario/prestamos/<int:prestamo_id>/devolucion/',
        legacy_bibliotecario_registrar_devolucion,
        name='legacy_bibliotecario_registrar_devolucion_alias_devolucion',
    ),
    path('', include(router.urls)),
]
