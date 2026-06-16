"""
FASE 5: Core URLs Configuration
Main URL routing
"""

from django.conf import settings
from django.conf.urls.static import static

from django.urls import path, include
from django.views.generic import RedirectView
from backend.apps.core.views.dashboard import dashboard
from backend.apps.core.views.dashboard_graficos import (
    api_datos_asistencia,
    api_datos_calificaciones,
    api_datos_estadisticas,
    api_datos_rendimiento,
    api_notificaciones,
    dashboard_graficos,
)
from backend.apps.core.views.seleccionar_escuela import seleccionar_escuela, entrar_escuela
from backend.apps.core.views.importar_datos import importar_datos
from backend.apps.core.views.estudiante.tareas import (
    calendario_tareas_estudiante,
    mi_asistencia_estudiante,
    ver_tareas_estudiante,
)
from backend.apps.core.views.estudiante.certificados import (
    descargar_certificado_matricula,
    descargar_certificado_notas,
    descargar_informe_rendimiento,
)
from backend.apps.core.views.admin_escolar.actualizar_escuela import actualizar_escuela
from backend.apps.core.views.admin_escolar.gestionar_infraestructura import gestionar_infraestructura
from backend.apps.core.views.admin_escolar.generar_informe_academico import generar_informe_academico
from backend.apps.core.views.admin_escolar.gestionar_estudiantes import gestionar_estudiantes
from backend.apps.core.views.admin_escolar.gestionar_profesores import gestionar_profesores
from backend.apps.core.views.admin_escolar.gestionar_apoderados import gestionar_apoderados
from backend.apps.core.views.admin_escolar.gestionar_cursos import gestionar_cursos
from backend.apps.core.views.admin_escolar.gestionar_ciclos import gestionar_ciclos
from backend.apps.core.views.admin_escolar.gestionar_asignaturas import gestionar_asignaturas
from backend.apps.core.views.admin_escolar.gestionar_asistencia_profesor import gestionar_asistencia_profesor
from backend.apps.core.views.admin_escolar.setup_checklist import setup_checklist
from backend.apps.core.views.admin_escolar.setup_wizard import setup_wizard
from backend.apps.core.views.admin_escolar.gestionar_evaluaciones_calificaciones import (
    gestionar_evaluaciones_calificaciones,
)
from backend.apps.academico.views.academic_management_views import crear_evaluacion_online_profesor
from backend.apps.academico.views.academic_report_views import (
    exportar_reporte_pdf,
    exportar_reporte_excel,
)
from backend.apps.core.views.admin_escolar.importar_datos_acciones import (
    editar_apoderado,
    editar_estudiante,
    editar_profesor,
    eliminar_usuario,
    importar_apoderados_csv,
    importar_estudiantes_csv,
    importar_profesores_csv,
    insertar_apoderado_manual,
    insertar_estudiante_manual,
    insertar_profesor_manual,
)
from backend.apps.core.views.ver_detalle_clase import ver_detalle_clase
from backend.apps.core.views.healthcheck import healthcheck
from backend.apps.core.views.pwa import service_worker
from backend.apps.core.views.admin_general.escuelas import (
    gestionar_escuelas,
    agregar_escuela,
    editar_escuela,
    detalle_escuela,
    eliminar_escuela,
    ajax_comunas_por_region,
)
from backend.apps.core.views.admin_general.api import (
    crear_usuario as admin_crear_usuario,
    toggle_estado_usuario,
    editar_usuario as admin_editar_usuario,
    crear_plan,
    editar_plan,
    crear_suscripcion,
    toggle_estado_suscripcion,
    guardar_configuracion_auditoria,
    exportar_auditoria_csv,
    exportar_estadisticas_globales_csv,
    exportar_reportes_financieros_csv,
)
from backend.apps.core.views.admin_escolar.reportes_api import exportar_reporte_cursos_csv
from backend.apps.core.views.profesor.gestionar_tareas import (
    gestionar_tareas_profesor,
    ver_detalle_entrega,
    ver_entregas_tarea,
)
from backend.apps.core.views.profesor.asistencia import (
    registro_asistencia_clase,
    reporte_asistencia_clase,
)
from backend.apps.core.views.profesor.libro_clases_api import (
    exportar_reporte_superintendencia,
    firmar_registro_profesor,
    guardar_registro_profesor,
    listar_auditoria_reporte_superintendencia,
    listar_registros_rbd,
    listar_registros_profesor,
)
from backend.apps.mensajeria.views import mensajes_clase
from backend.apps.core.views.asesor_financiero.dashboard_api import dashboard_kpis, dashboard_estadisticas
from backend.apps.core.views.asesor_financiero.estados_cuenta_api import listar_estados_cuenta
from backend.apps.core.views.asesor_financiero.pagos_api import listar_pagos
from backend.apps.core.views.asesor_financiero.cuotas_api import estadisticas_cuotas, listar_cuotas_proximas
from backend.apps.core.views.asesor_financiero.becas_api import (
    estadisticas_becas,
    listar_becas,
    buscar_estudiantes_beca,
    crear_beca,
)
from backend.apps.core.views.asesor_financiero.boletas_api import (
    estadisticas_boletas,
    listar_boletas,
)
from backend.apps.core.views.inspector_convivencia.api import (
    listar_estudiantes as inspector_listar_estudiantes,
    listar_justificativos as inspector_listar_justificativos,
    crear_anotacion,
    actualizar_justificativo,
    registrar_atraso as inspector_registrar_atraso,
)
from backend.apps.core.views.apoderado.api import (
    listar_justificativos as apoderado_listar_justificativos,
    crear_justificativo as apoderado_crear_justificativo,
    listar_documentos_firma as apoderado_listar_firmas,
    firmar_documento as apoderado_firmar_documento,
    crear_solicitud_admision as apoderado_crear_solicitud_admision,
    firmar_contrato as apoderado_firmar_contrato,
)
from backend.apps.core.views.estudiante.api import (
    entregar_tarea as estudiante_entregar_tarea
)
from backend.apps.core.views.psicologo_orientador.api import (
    listar_estudiantes as psicologo_listar_estudiantes,
    crear_entrevista,
    crear_derivacion,
    actualizar_derivacion,
    toggle_pie_status,
    listar_crear_citaciones,
    actualizar_citacion,
    listar_crear_casos_convivencia,
    actualizar_caso_convivencia,
)
from backend.apps.core.views.soporte_tecnico.api import (
    crear_ticket,
    actualizar_ticket,
    reset_password,
)
from backend.apps.core.views.bibliotecario_digital.api import (
    listar_recursos,
    listar_usuarios as bibliotecario_listar_usuarios,
    listar_prestamos as bibliotecario_listar_prestamos,
    crear_recurso,
    toggle_publicar_recurso,
    crear_prestamo,
    registrar_devolucion,
)
from backend.apps.core.views.coordinador_academico.api import (
    listar_planificaciones as coordinador_listar_planificaciones,
    actualizar_estado_planificacion,
)
from backend.apps.core.views.admin_escolar.finanzas_api import (
    registrar_pago_manual,
    listar_cuotas_estudiante,
    listar_cuotas_ciclo,
    condonar_cuota as admin_condonar_cuota,
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


urlpatterns = [
    # Redirección de la raíz a accounts (página de login)
    path('', RedirectView.as_view(url='/accounts/', permanent=False), name='home'),
    path('service-worker.js', service_worker, name='service_worker'),
    path('health/', healthcheck, name='healthcheck'),
    
    # Autenticación y cuentas
    path('accounts/', include('backend.apps.accounts.urls')),

    # API REST unificada v1
    path('api/v1/', include('backend.apps.api.urls')),
    
    # Dashboard principal
    path('dashboard/', dashboard, name='dashboard'),

    # Dashboard de estadísticas (migrado)
    path('dashboard-graficos/', dashboard_graficos, name='dashboard_graficos'),

    # Mensajería (migrado)
    path('mensajeria/', include(('backend.apps.mensajeria.urls', 'mensajeria'), namespace='mensajeria')),

    # Matrículas / Pagos (migrado)
    path('pagos/', include(('backend.apps.matriculas.urls', 'matriculas'), namespace='matriculas')),

    # Alias global usado por algunos templates legacy (iframe profesor)
    path('mensajeria/clase/<int:id_clase>/mensajes/', mensajes_clase, name='mensajes_clase'),

    # APIs para dashboard de gráficos (Chart.js)
    path('api/dashboard/asistencia/', api_datos_asistencia, name='api_datos_asistencia'),
    path('api/dashboard/calificaciones/', api_datos_calificaciones, name='api_datos_calificaciones'),
    path('api/dashboard/rendimiento/', api_datos_rendimiento, name='api_datos_rendimiento'),
    path('api/dashboard/estadisticas/', api_datos_estadisticas, name='api_datos_estadisticas'),
    path('api/dashboard/notificaciones/', api_notificaciones, name='api_notificaciones'),

    # Alias legacy /api para módulo importación/exportación (v1 sigue vigente en /api/v1)
    path('api/importacion/importar/', api_importar_datos, name='api_importar_datos_legacy_alias'),
    path('api/importacion/plantilla/<str:tipo>/', api_descargar_plantilla, name='api_descargar_plantilla_legacy_alias'),
    path('api/importacion/dashboard/', api_importacion_dashboard, name='api_importacion_dashboard_legacy_alias'),
    path('api/exportacion/estudiantes/', api_exportar_estudiantes, name='api_exportar_estudiantes_legacy_alias'),
    path('api/exportacion/profesores/', api_exportar_profesores, name='api_exportar_profesores_legacy_alias'),
    path('api/exportacion/reporte-academico/', api_exportar_reporte_academico, name='api_exportar_reporte_academico_legacy_alias'),
    path('api/exportacion/asistencia/', api_exportar_asistencia, name='api_exportar_asistencia_legacy_alias'),

    # APIs asesor financiero
    path('api/asesor-financiero/dashboard/kpis/', dashboard_kpis, name='api_dashboard_kpis'),
    path('api/asesor-financiero/dashboard/estadisticas/', dashboard_estadisticas, name='api_dashboard_estadisticas'),
    path('api/asesor-financiero/estados-cuenta/', listar_estados_cuenta, name='api_listar_estados_cuenta'),
    path('api/asesor-financiero/pagos/', listar_pagos, name='api_listar_pagos'),
    path('api/asesor-financiero/cuotas/estadisticas/', estadisticas_cuotas, name='api_cuotas_estadisticas'),
    path('api/asesor-financiero/cuotas/proximas/', listar_cuotas_proximas, name='api_cuotas_proximas'),
    path('api/asesor-financiero/becas/estadisticas/', estadisticas_becas, name='api_becas_estadisticas'),
    path('api/asesor-financiero/becas/', listar_becas, name='api_listar_becas'),
    path('api/asesor-financiero/becas/buscar-estudiantes/', buscar_estudiantes_beca, name='api_buscar_estudiantes_beca'),
    path('api/asesor-financiero/becas/crear/', crear_beca, name='api_crear_beca'),
    path('api/asesor-financiero/boletas/estadisticas/', estadisticas_boletas, name='api_boletas_estadisticas'),
    path('api/asesor-financiero/boletas/', listar_boletas, name='api_listar_boletas'),

    # Académico (global routes referenced by templates)
    path('estudiante/clase/<int:clase_id>/', ver_detalle_clase, name='ver_detalle_clase'),
    path('estudiante/tareas/', ver_tareas_estudiante, name='ver_tareas_estudiante'),
    path(
        'estudiante/calendario-tareas/',
        calendario_tareas_estudiante,
        name='calendario_tareas_estudiante',
    ),
    path('estudiante/mi-asistencia/', mi_asistencia_estudiante, name='mi_asistencia_estudiante'),
    
    # Profesor - Tareas
    path('profesor/gestionar-tareas/<int:clase_id>/', gestionar_tareas_profesor, name='gestionar_tareas_profesor'),
    path('profesor/entregas-tarea/<int:tarea_id>/', ver_entregas_tarea, name='ver_entregas_tarea'),
    path('profesor/entrega/<int:entrega_id>/', ver_detalle_entrega, name='ver_detalle_entrega'),
    
    # Profesor - Asistencia
    path('profesor/clase/<int:clase_id>/asistencia/', registro_asistencia_clase, name='registro_asistencia_clase'),
    path('profesor/clase/<int:clase_id>/asistencia/reporte/', reporte_asistencia_clase, name='reporte_asistencia_clase'),

    # Profesor - Reportes (exportación desde dashboard ?pagina=reportes)
    path('reportes/exportar-pdf/', exportar_reporte_pdf, name='exportar_reporte_pdf'),
    path('reportes/exportar-excel/', exportar_reporte_excel, name='exportar_reporte_excel'),

    # Profesor - Libro de Clases Digital
    path('api/profesor/libro-clases/', listar_registros_profesor, name='api_profesor_listar_registros_libro_clases'),
    path('api/profesor/libro-clases/registro/', guardar_registro_profesor, name='api_profesor_guardar_registro_libro_clases'),
    path('api/profesor/libro-clases/<int:registro_id>/firmar/', firmar_registro_profesor, name='api_profesor_firmar_registro_libro_clases'),
    path('api/coordinador/libro-clases/', listar_registros_rbd, name='api_coordinador_listar_registros_libro_clases'),
    path('api/admin-escolar/libro-clases/', listar_registros_rbd, name='api_admin_escolar_listar_registros_libro_clases'),

    # Reportes normativos - Superintendencia
    path('api/reportes/superintendencia/', exportar_reporte_superintendencia, name='api_exportar_reporte_superintendencia'),
    path('api/reportes/superintendencia/auditoria/', listar_auditoria_reporte_superintendencia, name='api_listar_auditoria_reporte_superintendencia'),

    # PDFs / Certificados (migrado desde sistema_antiguo)
    path(
        'pdf/certificado-notas/<int:estudiante_id>/',
        descargar_certificado_notas,
        name='descargar_certificado_notas',
    ),
    path(
        'pdf/certificado-matricula/<int:estudiante_id>/',
        descargar_certificado_matricula,
        name='descargar_certificado_matricula',
    ),
    path(
        'pdf/informe-rendimiento/<int:estudiante_id>/',
        descargar_informe_rendimiento,
        name='descargar_informe_rendimiento',
    ),

    # Admin escolar: actualizar datos de la escuela
    path('actualizar-escuela/', actualizar_escuela, name='actualizar_escuela'),

    # Admin escolar: CRUD infraestructura
    path('gestionar-infraestructura/', gestionar_infraestructura, name='gestionar_infraestructura'),

    # Admin escolar: generar informe académico (placeholder durante migración)
    path('generar-informe/<int:estudiante_id>/', generar_informe_academico, name='generar_informe_academico'),

    # Admin escolar: endpoint POST para acciones del módulo gestionar_estudiantes
    path('gestionar-estudiantes/', gestionar_estudiantes, name='gestionar_estudiantes'),
    path('gestionar-profesores/', gestionar_profesores, name='gestionar_profesores'),

    # Admin escolar: endpoint POST para acciones del módulo gestionar_apoderados
    path('gestionar-apoderados/', gestionar_apoderados, name='gestionar_apoderados'),

    # Admin escolar: endpoint POST para acciones del módulo gestionar_cursos
    path('gestionar-cursos/', gestionar_cursos, name='gestionar_cursos'),

    # Admin escolar: endpoint POST para acciones del módulo gestionar_ciclos
    path('gestionar-ciclos/', gestionar_ciclos, name='gestionar_ciclos'),

    # Admin escolar: Vista de checklist de configuración inicial
    path('setup/checklist/', setup_checklist, name='setup_checklist'),
    
    # Admin escolar: Wizard guiado de configuración inicial
    path('setup/wizard/', setup_wizard, name='setup_wizard'),

    # Admin escolar: CRUD asignaturas + asignaciones/horarios
    path('gestionar-asignaturas/', gestionar_asignaturas, name='gestionar_asignaturas'),

    # Profesor/Admin: endpoint POST para asistencia
    path('gestionar-asistencia-profesor/', gestionar_asistencia_profesor, name='gestionar_asistencia_profesor'),

    # Profesor/Admin: endpoint POST para evaluaciones y calificaciones
    path(
        'gestionar-evaluaciones-calificaciones/',
        gestionar_evaluaciones_calificaciones,
        name='gestionar_evaluaciones_calificaciones',
    ),
    path(
        'profesor/evaluaciones-online/',
        crear_evaluacion_online_profesor,
        name='crear_evaluacion_online_profesor',
    ),
    
    # Selección de escuela (Admin General)
    path('seleccionar-escuela/', seleccionar_escuela, name='seleccionar_escuela'),
    path('entrar-escuela/<int:rbd>/', entrar_escuela, name='entrar_escuela'),

    # Gestión de Datos - Importar/Insertar
    path('importar-datos/', importar_datos, name='importar_datos'),

    # Gestión de Datos - Acciones (placeholders durante migración)
    path('insertar-estudiante/', insertar_estudiante_manual, name='insertar_estudiante_manual'),
    path('insertar-profesor/', insertar_profesor_manual, name='insertar_profesor_manual'),
    path('insertar-apoderado/', insertar_apoderado_manual, name='insertar_apoderado_manual'),
    path('importar-estudiantes-csv/', importar_estudiantes_csv, name='importar_estudiantes_csv'),
    path('importar-profesores-csv/', importar_profesores_csv, name='importar_profesores_csv'),
    path('importar-apoderados-csv/', importar_apoderados_csv, name='importar_apoderados_csv'),
    path('editar-estudiante/<int:estudiante_id>/', editar_estudiante, name='editar_estudiante'),
    path('editar-profesor/<int:profesor_id>/', editar_profesor, name='editar_profesor'),
    path('editar-apoderado/<int:apoderado_id>/', editar_apoderado, name='editar_apoderado'),
    path('eliminar-usuario/<int:usuario_id>/', eliminar_usuario, name='eliminar_usuario'),

    # Admin General - Gestión de Escuelas
    path('admin-general/escuelas/', gestionar_escuelas, name='admin_general_escuelas'),
    path('admin-general/agregar-escuela/', agregar_escuela, name='admin_general_agregar_escuela'),
    path('admin-general/editar-escuela/<int:rbd>/', editar_escuela, name='admin_general_editar_escuela'),
    path('admin-general/detalle-escuela/<int:rbd>/', detalle_escuela, name='admin_general_detalle_escuela'),
    path('admin-general/eliminar-escuela/<int:rbd>/', eliminar_escuela, name='admin_general_eliminar_escuela'),
    path('admin-general/comunas-por-region/<int:region_id>/', ajax_comunas_por_region, name='admin_general_comunas_por_region'),

    # Admin General — APIs (usuarios, planes, suscripciones, config)
    path('api/admin-general/usuarios/crear/', admin_crear_usuario, name='api_admin_general_crear_usuario'),
    path('api/admin-general/usuarios/<int:user_id>/toggle-estado/', toggle_estado_usuario, name='api_admin_general_toggle_estado_usuario'),
    path('api/admin-general/usuarios/<int:user_id>/editar/', admin_editar_usuario, name='api_admin_general_editar_usuario'),
    path('api/admin-general/planes/crear/', crear_plan, name='api_admin_general_crear_plan'),
    path('api/admin-general/planes/<int:plan_id>/editar/', editar_plan, name='api_admin_general_editar_plan'),
    path('api/admin-general/suscripciones/crear/', crear_suscripcion, name='api_admin_general_crear_suscripcion'),
    path('api/admin-general/suscripciones/<int:subscription_id>/toggle-estado/', toggle_estado_suscripcion, name='api_admin_general_toggle_suscripcion'),
    path('api/admin-general/configuracion/auditoria/', guardar_configuracion_auditoria, name='api_admin_general_config_auditoria'),
    path('api/admin-general/auditoria/exportar/', exportar_auditoria_csv, name='api_admin_general_exportar_auditoria'),
    path('api/admin-general/estadisticas/exportar/', exportar_estadisticas_globales_csv, name='api_admin_general_exportar_estadisticas'),
    path('api/admin-general/reportes-financieros/exportar/', exportar_reportes_financieros_csv, name='api_admin_general_exportar_reportes_financieros'),

    # -------------------------------------------------------------------
    # Inspector Convivencia — APIs
    # -------------------------------------------------------------------
    path('api/inspector/estudiantes/', inspector_listar_estudiantes, name='api_inspector_listar_estudiantes'),
    path('api/inspector/justificativos/', inspector_listar_justificativos, name='api_inspector_listar_justificativos'),
    path('api/inspector/anotaciones/crear/', crear_anotacion, name='api_inspector_crear_anotacion'),
    path('api/inspector/justificativos/<int:justificativo_id>/estado/', actualizar_justificativo, name='api_inspector_actualizar_justificativo'),
    path('api/inspector/asistencia/registrar_atraso/', inspector_registrar_atraso, name='api_inspector_registrar_atraso'),

    # -------------------------------------------------------------------
    # Estudiante — APIs
    # -------------------------------------------------------------------
    path('api/estudiante/tareas/entregar/', estudiante_entregar_tarea, name='api_estudiante_entregar_tarea'),

    # -------------------------------------------------------------------
    # Apoderado — APIs
    # -------------------------------------------------------------------
    path('api/apoderado/justificativos/', apoderado_listar_justificativos, name='api_apoderado_listar_justificativos'),
    path('api/apoderado/justificativos/crear/', apoderado_crear_justificativo, name='api_apoderado_crear_justificativo'),
    path('api/apoderado/firmas/', apoderado_listar_firmas, name='api_apoderado_listar_firmas'),
    path('api/apoderado/firmas/firmar/', apoderado_firmar_documento, name='api_apoderado_firmar_documento'),
    path('api/apoderado/admisiones/solicitar/', apoderado_crear_solicitud_admision, name='api_apoderado_crear_solicitud'),
    path('api/apoderado/admisiones/firmar-contrato/', apoderado_firmar_contrato, name='api_apoderado_firmar_contrato'),

    # -------------------------------------------------------------------
    # Psicólogo Orientador — APIs
    # -------------------------------------------------------------------
    path('api/psicologo/estudiantes/', psicologo_listar_estudiantes, name='api_psicologo_listar_estudiantes'),
    path('api/psicologo/estudiantes/<int:estudiante_id>/pie/', toggle_pie_status, name='api_psicologo_toggle_pie'),
    path('api/psicologo/entrevistas/crear/', crear_entrevista, name='api_psicologo_crear_entrevista'),
    path('api/psicologo/derivaciones/crear/', crear_derivacion, name='api_psicologo_crear_derivacion'),
    path('api/psicologo/derivaciones/<int:derivacion_id>/', actualizar_derivacion, name='api_psicologo_actualizar_derivacion'),
    path('api/psicologo/citaciones/', listar_crear_citaciones, name='api_psicologo_citaciones'),
    path('api/psicologo/citaciones/<int:citacion_id>/actualizar/', actualizar_citacion, name='api_psicologo_actualizar_citacion'),
    path('api/psicologo/casos-convivencia/', listar_crear_casos_convivencia, name='api_psicologo_casos_convivencia'),
    path('api/psicologo/casos-convivencia/<int:caso_id>/actualizar/', actualizar_caso_convivencia, name='api_psicologo_actualizar_caso'),

    # -------------------------------------------------------------------
    # Coordinador Académico — APIs
    # -------------------------------------------------------------------
    path('api/coordinador/planificaciones/', coordinador_listar_planificaciones, name='api_coordinador_listar_planificaciones'),
    path('api/coordinador/planificaciones/<int:planificacion_id>/estado/', actualizar_estado_planificacion, name='api_coordinador_actualizar_planificacion'),

    # -------------------------------------------------------------------
    # Admin Escolar — Finanzas APIs
    # -------------------------------------------------------------------
    path('api/admin-escolar/finanzas/registrar-pago/', registrar_pago_manual, name='api_admin_registrar_pago'),
    path('api/admin-escolar/finanzas/cuotas-estudiante/', listar_cuotas_estudiante, name='api_admin_cuotas_estudiante'),
    path('api/admin-escolar/finanzas/cuotas-ciclo/', listar_cuotas_ciclo, name='api_admin_cuotas_ciclo'),
    path('api/admin-escolar/finanzas/condonar-cuota/', admin_condonar_cuota, name='api_admin_condonar_cuota'),
    path('api/admin-escolar/reportes/cursos/exportar/', exportar_reporte_cursos_csv, name='api_admin_escolar_exportar_reporte_cursos'),

    # -------------------------------------------------------------------
    # Soporte Técnico Escolar — APIs
    # -------------------------------------------------------------------
    path('api/soporte/tickets/crear/', crear_ticket, name='api_soporte_crear_ticket'),
    path('api/soporte/tickets/<int:ticket_id>/estado/', actualizar_ticket, name='api_soporte_actualizar_ticket'),
    path('api/soporte/usuarios/<int:user_id>/reset_password/', reset_password, name='api_soporte_reset_password'),

    # -------------------------------------------------------------------
    # Bibliotecario Digital — APIs
    # -------------------------------------------------------------------
    path('api/bibliotecario/recursos/', listar_recursos, name='api_bibliotecario_listar_recursos'),
    path('api/bibliotecario/usuarios/', bibliotecario_listar_usuarios, name='api_bibliotecario_listar_usuarios'),
    path('api/bibliotecario/prestamos/', bibliotecario_listar_prestamos, name='api_bibliotecario_listar_prestamos'),
    path('api/bibliotecario/recursos/crear/', crear_recurso, name='api_bibliotecario_crear_recurso'),
    path('api/bibliotecario/recursos/<int:recurso_id>/publicar/', toggle_publicar_recurso, name='api_bibliotecario_toggle_publicar'),
    path('api/bibliotecario/prestamos/crear/', crear_prestamo, name='api_bibliotecario_crear_prestamo'),
    path('api/bibliotecario/prestamos/<int:prestamo_id>/devolver/', registrar_devolucion, name='api_bibliotecario_devolucion'),

    # Seguridad
    path('seguridad/', include('backend.apps.security.urls')),

    # Seleccion de comunicados
    path("comunicados/", include("backend.apps.comunicados.urls")),
]

if settings.DEBUG and getattr(settings, 'DEBUG_TOOLBAR_ENABLED', False):
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
