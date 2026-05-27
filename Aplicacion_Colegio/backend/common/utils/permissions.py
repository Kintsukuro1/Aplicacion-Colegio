"""
Utilidades de permisos y rutas por rol
"""


def get_paginas_por_rol(rol):
    """
    Retorna el mapeo de páginas permitidas por rol

    Args:
        rol (str): Nombre del rol normalizado (admin, admin_escolar, profesor, etc.)

    Returns:
        dict: Diccionario con las páginas permitidas para el rol
              Formato: {nombre_pagina: ruta_template}

    Examples:
        >>> paginas = get_paginas_por_rol('profesor')
        >>> paginas['mis_clases']
        'profesor/mis_clases.html'
    """
    paginas = {
        'admin': {
            'inicio': 'compartido/inicio_modulos.html',
            'gestionar_escuelas': 'admin/seleccionar_escuela.html',
            'perfil': 'compartido/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'admin_general': {
            'inicio': 'compartido/inicio_modulos.html',
            'gestionar_escuelas': 'admin/seleccionar_escuela.html',
            'perfil': 'compartido/perfil.html',
            'escuelas': 'admin/escuelas.html',
            'usuarios': 'admin/usuarios.html',
            'planes': 'admin/planes.html',
            'estadisticas_globales': 'admin/estadisticas_globales.html',
            'reportes_financieros': 'admin/reportes_financieros.html',
            'configuracion': 'admin/configuracion.html',
            'auditoria': 'admin/auditoria.html',
            'monitoreo_seguridad': 'admin/monitoreo_seguridad.html',
            'calendario_eventos': 'compartido/calendario_eventos.html',
            'solicitud_reuniones': 'compartido/solicitud_reuniones.html',
            'active_sessions': 'compartido/active_sessions.html',
            'password_history': 'compartido/password_history.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'admin_escolar': {
            'inicio': 'compartido/inicio_modulos.html',
            'mi_escuela': 'admin_escolar/mi_escuela.html',
            'infraestructura': 'admin_escolar/infraestructura.html',
            'gestionar_estudiantes': 'admin_escolar/gestionar_estudiantes.html',
            'gestionar_apoderados': 'admin_escolar/gestionar_apoderados.html',
            'gestionar_cursos': 'admin_escolar/gestionar_cursos.html',
            'gestionar_ciclos': 'admin_escolar/gestionar_ciclos.html',
            'gestionar_asignaturas': 'admin_escolar/gestionar_asignaturas.html',
            'gestionar_finanzas': 'admin_escolar/gestionar_finanzas.html',
            'gestionar_profesores': 'admin_escolar/gestionar_profesores.html',
            'asistencia': 'profesor/asistencia.html',
            'notas': 'profesor/notas.html',
            'libro_notas': 'profesor/notas.html',
            'libro_clases': 'profesor/libro_clases.html',
            'informes_reportes': 'profesor/reportes.html',
            'reportes': 'profesor/reportes.html',
            'calendario_eventos': 'compartido/calendario_eventos.html',
            'solicitud_reuniones': 'compartido/solicitud_reuniones.html',
            'active_sessions': 'compartido/active_sessions.html',
            'password_history': 'compartido/password_history.html',
            'perfil': 'admin_escolar/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'profesor': {
            'inicio': 'compartido/inicio_modulos.html',
            'mis_clases': 'profesor/mis_clases.html',
            'asistencia': 'profesor/asistencia.html',
            'notas': 'profesor/notas.html',
            'libro_clases': 'profesor/libro_clases.html',
            'reportes': 'profesor/reportes.html',
            'disponibilidad': 'profesor/disponibilidad.html',
            'tareas_consolidado': 'profesor/tareas_consolidado.html',
            'mis_planificaciones': 'profesor/mis_planificaciones.html',
            'calendario_eventos': 'compartido/calendario_eventos.html',
            'solicitud_reuniones': 'compartido/solicitud_reuniones.html',
            'perfil': 'profesor/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'estudiante': {
            'inicio': 'estudiante/inicio.html',
            'mis_clases': 'estudiante/mis_clases.html',
            'mi_horario': 'estudiante/mi_horario.html',
            'mis_evaluaciones': 'estudiante/mis_evaluaciones.html',
            'mis_notas': 'estudiante/mis_notas.html',
            'asistencia': 'estudiante/asistencia.html',
            'mi_asistencia': 'estudiante/asistencia.html',
            'mis_tareas': 'estudiante/mis_tareas.html',
            'mis_anotaciones': 'estudiante/mis_anotaciones.html',
            'mis_certificados': 'estudiante/mis_certificados.html',
            'perfil': 'compartido/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'apoderado': {
            'inicio': 'apoderado/inicio.html',
            'mis_pupilos': 'apoderado/mis_pupilos.html',
            'notas': 'apoderado/notas.html',
            'asistencia': 'apoderado/asistencia.html',
            'mis_certificados': 'apoderado/mis_certificados.html',
            'justificativos': 'apoderado/justificativos.html',
            'firmas_pendientes': 'apoderado/firmas_pendientes.html',
            'admision_matricula': 'apoderado/admision_matricula.html',
            'calendario_pupilo': 'apoderado/calendario_pupilo.html',
            'perfil': 'apoderado/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'asesor_financiero': {
            'inicio': 'asesor_financiero/inicio.html',
            'dashboard_financiero': 'asesor_financiero/dashboard.html',
            'estados_cuenta': 'asesor_financiero/estados_cuenta.html',
            'pagos': 'asesor_financiero/pagos.html',
            'cuotas': 'asesor_financiero/cuotas.html',
            'becas': 'asesor_financiero/becas.html',
            'boletas': 'asesor_financiero/boletas.html',
            'reportes': 'asesor_financiero/reportes.html',
            'configuracion_transbank': 'asesor_financiero/configuracion_transbank.html',
            'perfil': 'compartido/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'coordinador_academico': {
            'inicio': 'coordinador_academico/inicio.html',
            'rendimiento': 'coordinador_academico/rendimiento.html',
            'profesores': 'coordinador_academico/profesores.html',
            'planificacion': 'coordinador_academico/planificacion.html',
            'perfil': 'compartido/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'inspector_convivencia': {
            'inicio': 'inspector_convivencia/inicio.html',
            'anotaciones': 'inspector_convivencia/anotaciones.html',
            'justificativos': 'inspector_convivencia/justificativos.html',
            'asistencia': 'inspector_convivencia/asistencia.html',
            'perfil': 'compartido/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'psicologo_orientador': {
            'inicio': 'psicologo_orientador/inicio.html',
            'entrevistas': 'psicologo_orientador/entrevistas.html',
            'derivaciones': 'psicologo_orientador/derivaciones.html',
            'ficha_estudiante': 'psicologo_orientador/ficha_estudiante.html',
            'citaciones_casos': 'psicologo_orientador/citaciones_casos.html',
            'perfil': 'compartido/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'soporte_tecnico_escolar': {
            'inicio': 'soporte_tecnico_escolar/inicio.html',
            'tickets': 'soporte_tecnico_escolar/tickets.html',
            'usuarios': 'soporte_tecnico_escolar/usuarios.html',
            'actividad': 'soporte_tecnico_escolar/actividad.html',
            'perfil': 'compartido/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
        'bibliotecario_digital': {
            'inicio': 'bibliotecario_digital/inicio.html',
            'catalogo': 'bibliotecario_digital/catalogo.html',
            'prestamos': 'bibliotecario_digital/prestamos.html',
            'perfil': 'compartido/perfil.html',
            'notificaciones': 'compartido/notificaciones.html',
        },
    }

    return paginas.get(rol, {})


def get_permisos_por_rol(rol):
    """
    Retorna los permisos por acción para cada rol

    Args:
        rol (str): Nombre del rol normalizado

    Returns:
        dict: Diccionario con permisos por acción
              Formato: {accion: bool}
    """
    permisos_base = {
        # Permisos de lectura (todos los roles autenticados)
        'ver_perfil_propio': True,
        'ver_dashboard': True,

        # Permisos de escritura (restringidos)
        'crear_usuario': False,
        'modificar_usuario': False,
        'eliminar_usuario': False,

        'crear_colegio': False,
        'modificar_colegio': False,
        'eliminar_colegio': False,

        'crear_curso': False,
        'modificar_curso': False,
        'eliminar_curso': False,

        'crear_asignatura': False,
        'modificar_asignatura': False,
        'eliminar_asignatura': False,

        'crear_clase': False,
        'modificar_clase': False,
        'eliminar_clase': False,

        'crear_matricula': False,
        'modificar_matricula': False,
        'eliminar_matricula': False,

        'crear_cuota': False,
        'modificar_cuota': False,
        'eliminar_cuota': False,

        'crear_pago': False,
        'modificar_pago': False,
        'eliminar_pago': False,

        'crear_beca': False,
        'modificar_beca': False,
        'aprobar_beca': False,
        'rechazar_beca': False,
        'eliminar_beca': False,

        'crear_boleta': False,
        'modificar_boleta': False,
        'anular_boleta': False,
        'eliminar_boleta': False,

        'crear_comunicado': False,
        'modificar_comunicado': False,
        'eliminar_comunicado': False,

        'ver_datos_sensibles': False,
        'exportar_datos': False,
        'ver_logs_sistema': False,
    }

    # Permisos específicos por rol
    permisos_por_rol = {
        'admin': {
            # Administrador general tiene todos los permisos
            **permisos_base,
            'crear_usuario': True,
            'modificar_usuario': True,
            'eliminar_usuario': True,
            'crear_colegio': True,
            'modificar_colegio': True,
            'eliminar_colegio': True,
            'ver_datos_sensibles': True,
            'exportar_datos': True,
            'ver_logs_sistema': True,
        },
        'admin_escolar': {
            **permisos_base,
            # Administrador escolar puede gestionar su colegio
            'crear_usuario': True,  # Solo usuarios de su colegio
            'modificar_usuario': True,  # Solo usuarios de su colegio
            'eliminar_usuario': True,  # Solo usuarios de su colegio
            'crear_curso': True,
            'modificar_curso': True,
            'eliminar_curso': True,
            'crear_asignatura': True,
            'modificar_asignatura': True,
            'eliminar_asignatura': True,
            'crear_clase': True,
            'modificar_clase': True,
            'eliminar_clase': True,
            'crear_matricula': True,
            'modificar_matricula': True,
            'eliminar_matricula': True,
            'crear_comunicado': True,
            'modificar_comunicado': True,
            'eliminar_comunicado': True,
            'ver_datos_sensibles': True,  # Solo datos de su colegio
            'exportar_datos': True,  # Solo datos de su colegio
        },
        'profesor': {
            **permisos_base,
            # Profesor puede gestionar sus clases
            'crear_clase': True,  # Solo sus clases
            'modificar_clase': True,  # Solo sus clases
            'eliminar_clase': True,  # Solo sus clases
            'crear_comunicado': True,  # Solo para sus cursos
            'modificar_comunicado': True,  # Solo sus comunicados
            'eliminar_comunicado': True,  # Solo sus comunicados
        },
        'estudiante': {
            **permisos_base,
            # Estudiante solo puede ver sus propios datos
        },
        'apoderado': {
            **permisos_base,
            # Apoderado puede ver datos de sus pupilos
        },
        'asesor_financiero': {
            **permisos_base,
            # Asesor financiero gestiona finanzas de su colegio
            'crear_cuota': True,
            'modificar_cuota': True,
            'eliminar_cuota': True,
            'crear_pago': True,
            'modificar_pago': True,
            'eliminar_pago': True,
            'crear_beca': True,
            'modificar_beca': True,
            'aprobar_beca': True,
            'rechazar_beca': True,
            'eliminar_beca': True,
            'crear_boleta': True,
            'modificar_boleta': True,
            'anular_boleta': True,
            'eliminar_boleta': True,
            'ver_datos_sensibles': True,
            'exportar_datos': True,
        },
        'coordinador_academico': {
            **permisos_base,
            'exportar_datos': True,
        },
        'inspector_convivencia': {
            **permisos_base,
        },
        'psicologo_orientador': {
            **permisos_base,
            'ver_datos_sensibles': True,
        },
        'soporte_tecnico_escolar': {
            **permisos_base,
            'modificar_usuario': True,
            'ver_logs_sistema': True,
        },
        'bibliotecario_digital': {
            **permisos_base,
            'crear_comunicado': True,
            'modificar_comunicado': True,
        },
    }

    return permisos_por_rol.get(rol, permisos_base)


def validar_permiso_usuario(user, permiso_requerido):
    """
    Valida si un usuario tiene un permiso específico

    Args:
        user: Usuario de Django
        permiso_requerido (str): Nombre del permiso requerido

    Returns:
        bool: True si tiene el permiso, False en caso contrario
    """
    from backend.common.services.policy_service import PolicyService
    from backend.common.services.permission_service import PermissionService

    if not user or not user.is_authenticated:
        return False

    permiso_to_capability = {
        'ver_estudiantes': 'STUDENT_VIEW',
        'crear_estudiante': 'STUDENT_CREATE',
        'modificar_estudiante': 'STUDENT_EDIT',
        'eliminar_estudiante': 'STUDENT_DELETE',
        'ver_profesores': 'TEACHER_VIEW',
        'crear_profesor': 'TEACHER_CREATE',
        'modificar_profesor': 'TEACHER_EDIT',
        'eliminar_profesor': 'TEACHER_DELETE',
        'ver_cursos': 'COURSE_VIEW',
        'crear_curso': 'COURSE_CREATE',
        'modificar_curso': 'COURSE_EDIT',
        'eliminar_curso': 'COURSE_DELETE',
        'ver_notas': 'GRADE_VIEW',
        'crear_nota': 'GRADE_CREATE',
        'modificar_nota': 'GRADE_EDIT',
        'eliminar_nota': 'GRADE_DELETE',
        'ver_asistencia': 'CLASS_VIEW_ATTENDANCE',
        'modificar_asistencia': 'CLASS_TAKE_ATTENDANCE',
        'ver_reportes': 'REPORT_VIEW_BASIC',
        'ver_finanzas': 'FINANCE_VIEW',
        'crear_pago': 'FINANCE_CREATE',
        'modificar_pago': 'FINANCE_EDIT',
        'eliminar_pago': 'FINANCE_DELETE',
        'ver_usuarios': 'USER_VIEW',
        'crear_usuario': 'USER_CREATE',
        'modificar_usuario': 'USER_EDIT',
        'eliminar_usuario': 'USER_DELETE',
        'asignar_roles': 'USER_ASSIGN_ROLE',
        'configurar_sistema': 'SYSTEM_CONFIGURE',
    }

    mapped_capability = permiso_to_capability.get(permiso_requerido)
    if mapped_capability and PolicyService.has_capability(user, mapped_capability):
        return True

    permiso_to_legacy = {
        'ver_estudiantes': ('ACADEMICO', 'VIEW_STUDENTS'),
        'crear_estudiante': ('ACADEMICO', 'MANAGE_STUDENTS'),
        'modificar_estudiante': ('ACADEMICO', 'MANAGE_STUDENTS'),
        'eliminar_estudiante': ('ACADEMICO', 'MANAGE_STUDENTS'),
        'ver_profesores': ('ACADEMICO', 'VIEW_COURSES'),
        'crear_profesor': ('ADMINISTRATIVO', 'MANAGE_USERS'),
        'modificar_profesor': ('ADMINISTRATIVO', 'MANAGE_USERS'),
        'eliminar_profesor': ('ADMINISTRATIVO', 'MANAGE_USERS'),
        'ver_cursos': ('ACADEMICO', 'VIEW_COURSES'),
        'crear_curso': ('ACADEMICO', 'MANAGE_COURSES'),
        'modificar_curso': ('ACADEMICO', 'MANAGE_COURSES'),
        'eliminar_curso': ('ACADEMICO', 'MANAGE_COURSES'),
        'ver_notas': ('ACADEMICO', 'VIEW_GRADES'),
        'crear_nota': ('ACADEMICO', 'EDIT_GRADES'),
        'modificar_nota': ('ACADEMICO', 'EDIT_GRADES'),
        'eliminar_nota': ('ACADEMICO', 'EDIT_GRADES'),
        'ver_asistencia': ('ACADEMICO', 'VIEW_ATTENDANCE'),
        'modificar_asistencia': ('ACADEMICO', 'EDIT_ATTENDANCE'),
        'ver_reportes': ('ADMINISTRATIVO', 'VIEW_REPORTS'),
        'ver_finanzas': ('FINANCIERO', 'VIEW_PAYMENTS'),
        'crear_pago': ('FINANCIERO', 'PROCESS_PAYMENTS'),
        'modificar_pago': ('FINANCIERO', 'PROCESS_PAYMENTS'),
        'eliminar_pago': ('FINANCIERO', 'PROCESS_PAYMENTS'),
        'ver_usuarios': ('ADMINISTRATIVO', 'MANAGE_USERS'),
        'crear_usuario': ('ADMINISTRATIVO', 'MANAGE_USERS'),
        'modificar_usuario': ('ADMINISTRATIVO', 'MANAGE_USERS'),
        'eliminar_usuario': ('ADMINISTRATIVO', 'MANAGE_USERS'),
        'asignar_roles': ('ADMINISTRATIVO', 'MANAGE_USERS'),
        'configurar_sistema': ('ADMINISTRATIVO', 'MANAGE_SYSTEM'),
    }

    legacy_permission = permiso_to_legacy.get(permiso_requerido)
    if legacy_permission:
        module, action = legacy_permission
        return PermissionService.has_permission(user, module, action)

    return False


def validar_acceso_colegio(user, colegio_id):
    """
    Valida que el usuario tenga acceso al colegio especificado

    Args:
        user: Usuario de Django
        colegio_id: ID del colegio

    Returns:
        bool: True si tiene acceso, False en caso contrario
    """
    if not user or not user.is_authenticated:
        return False

    # Administrador de sistema tiene acceso a todos los colegios
    from backend.common.services.policy_service import PolicyService
    if PolicyService.has_capability(user, 'SYSTEM_ADMIN'):
        return True

    # Otros roles solo tienen acceso a su colegio asignado
    return user.rbd_colegio == colegio_id
