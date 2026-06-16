"""
ComunicadosService - Servicio para gestión de comunicados

Este servicio centraliza la lógica de negocio para:
- Filtrar comunicados según roles y permisos
- Crear y gestionar comunicados
- Manejar confirmaciones de lectura
- Calcular estadísticas de comunicados
- Gestionar adjuntos
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from django.db.models import Q, Count
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist

from backend.common.validations import CommonValidations
from backend.common.services import PermissionService
from backend.common.services.policy_service import PolicyService
from backend.common.exceptions import PrerequisiteException
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService

logger = logging.getLogger('comunicados')


class ComunicadosService:
    """
    Servicio para gestión completa de comunicados
    """

    @staticmethod
    def execute(operation: str, params: Dict[str, Any]) -> Any:
        """Punto de entrada estándar del servicio (fase 3.1)."""
        ComunicadosService.validate(operation, params)
        return ComunicadosService._execute(operation, params)

    @staticmethod
    def validate(operation: str, params: Dict[str, Any]) -> None:
        """Valida parámetros mínimos requeridos por operación."""
        if operation == 'create_comunicado':
            if params.get('user') is None:
                raise ValueError('Parámetro requerido: user')
            if params.get('data') is None:
                raise ValueError('Parámetro requerido: data')
            if params.get('files') is None:
                raise ValueError('Parámetro requerido: files')
            return
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _execute(operation: str, params: Dict[str, Any]) -> Any:
        """Despacha operaciones a implementaciones privadas."""
        if operation == 'create_comunicado':
            return ComunicadosService._execute_create_comunicado(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def _is_school_admin(user) -> bool:
        return PolicyService.has_capability(
            user,
            'SYSTEM_CONFIGURE',
            school_id=getattr(user, 'rbd_colegio', None),
        )

    @staticmethod
    def _is_teacher(user) -> bool:
        return PolicyService.has_capability(
            user,
            'TEACHER_VIEW',
            school_id=getattr(user, 'rbd_colegio', None),
        )

    @staticmethod
    def _is_student(user) -> bool:
        school_id = getattr(user, 'rbd_colegio', None)
        can_view_class = PolicyService.has_capability(user, 'CLASS_VIEW', school_id=school_id)
        can_view_grades = PolicyService.has_capability(user, 'GRADE_VIEW', school_id=school_id)
        can_view_students = PolicyService.has_capability(user, 'STUDENT_VIEW', school_id=school_id)
        can_view_teachers = PolicyService.has_capability(user, 'TEACHER_VIEW', school_id=school_id)
        return can_view_class and can_view_grades and not can_view_students and not can_view_teachers

    @staticmethod
    def _has_profile(user, profile_attr: str) -> bool:
        user_dict = getattr(user, '__dict__', {})
        if profile_attr in user_dict:
            return user_dict.get(profile_attr) is not None

        if getattr(type(user), profile_attr, None) is None:
            return False

        try:
            return getattr(user, profile_attr, None) is not None
        except (ObjectDoesNotExist, AttributeError):
            return False

    @staticmethod
    def get_comunicados_for_user(user) -> List:
        """
        Obtiene comunicados filtrados según el rol del usuario

        Args:
            user: Usuario de Django

        Returns:
            QuerySet: Comunicados filtrados
        """
        from ..models import Comunicado
        from backend.apps.accounts.models import PerfilEstudiante

        base_filters = Q(colegio=user.colegio, activo=True)

        if ComunicadosService._is_school_admin(user):
            comunicados = Comunicado.objects.filter(base_filters)
        elif ComunicadosService._is_teacher(user):
            comunicados = Comunicado.objects.filter(
                base_filters &
                (Q(destinatario='todos') | Q(destinatario='profesores'))
            )
        elif ComunicadosService._is_student(user):
            # Obtener curso del estudiante
            try:
                perfil = PerfilEstudiante.objects.get(user=user)
                curso_actual = perfil.curso_actual
            except PerfilEstudiante.DoesNotExist:
                curso_actual = None

            comunicados = Comunicado.objects.filter(
                base_filters &
                (
                    Q(destinatario='todos') |
                    Q(destinatario='estudiantes') |
                    Q(destinatario='apoderados') |
                    (Q(destinatario='curso_especifico') & Q(cursos_destinatarios=curso_actual))
                )
            ).distinct()
        elif ComunicadosService._has_profile(user, 'perfil_apoderado'):
            # Fix: la rama else solo mostraba destinatario='todos' y ocultaba comunicados al apoderado.
            from backend.apps.matriculas.models import Matricula

            apoderado = getattr(user, 'perfil_apoderado', None)
            pupil_ids = list(apoderado.estudiantes.values_list('id', flat=True)) if apoderado else []
            course_ids = list(
                Matricula.objects.filter(
                    estudiante_id__in=pupil_ids,
                    estado='ACTIVA',
                )
                .exclude(curso_id__isnull=True)
                .values_list('curso_id', flat=True)
            )

            comunicados = Comunicado.objects.filter(
                base_filters &
                (
                    Q(destinatario='todos') |
                    Q(destinatario='apoderados') |
                    (
                        Q(destinatario='curso_especifico') &
                        Q(cursos_destinatarios__in=course_ids)
                    )
                )
            ).distinct()
        else:
            # Para otros roles, solo comunicados generales
            comunicados = Comunicado.objects.filter(
                base_filters & Q(destinatario='todos')
            )

        return comunicados.select_related(
            'publicado_por',
            'colegio',
        ).prefetch_related(
            'cursos_destinatarios',
        ).order_by('-es_destacado', '-fecha_publicacion')

    @staticmethod
    def get_comunicado_or_none(comunicado_id: int):
        from ..models import Comunicado

        return Comunicado.objects.select_related(
            'publicado_por',
            'colegio',
        ).prefetch_related(
            'cursos_destinatarios',
        ).filter(id_comunicado=comunicado_id).first()

    @staticmethod
    def filter_comunicados_by_type(comunicados, tipo_filtro: str):
        """
        Filtra comunicados por tipo

        Args:
            comunicados: QuerySet de comunicados
            tipo_filtro: Tipo a filtrar

        Returns:
            QuerySet: Comunicados filtrados
        """
        if tipo_filtro:
            return comunicados.filter(tipo=tipo_filtro)
        return comunicados

    @staticmethod
    def _comunicado_es_urgente(comunicado) -> bool:
        return comunicado.tipo == 'urgente' or comunicado.es_prioritario

    @staticmethod
    def get_profesor_comunicados_list_context(comunicados) -> Dict[str, Any]:
        """
        Métricas, alertas y prioridades para la lista premium del profesor.
        Usa la bandeja completa (sin filtro de tipo) para contadores e inteligencia.
        """
        from django.utils import timezone

        items = list(comunicados)
        total = len(items)
        urgentes = sum(1 for c in items if ComunicadosService._comunicado_es_urgente(c))
        citaciones = sum(1 for c in items if c.tipo == 'citacion')
        eventos = sum(1 for c in items if c.tipo == 'evento')
        prioritarios = sum(1 for c in items if c.es_prioritario)
        confirmacion = sum(1 for c in items if c.requiere_confirmacion)
        destacados = sum(1 for c in items if c.es_destacado)

        now = timezone.now()
        proximos = sorted(
            [c for c in items if getattr(c, 'fecha_evento', None) and c.fecha_evento >= now],
            key=lambda c: c.fecha_evento,
        )[:3]

        alertas = []
        if urgentes:
            alertas.append(
                f'Tienes {urgentes} comunicado{"s" if urgentes != 1 else ""} '
                f'urgente{"s" if urgentes != 1 else ""} o prioritario{"s" if urgentes != 1 else ""}: '
                'revísalos antes del resto.'
            )
        if citaciones:
            alertas.append(
                f'{citaciones} citación{"es" if citaciones != 1 else ""} '
                f'con fecha de reunión o entrevista.'
            )
        if confirmacion:
            alertas.append(
                f'{confirmacion} comunicado{"s" if confirmacion != 1 else ""} '
                'piden confirmación de lectura al abrir el detalle.'
            )

        prioridad = sorted(
            [
                c for c in items
                if ComunicadosService._comunicado_es_urgente(c)
                or c.tipo in ('citacion', 'urgente')
                or c.es_prioritario
            ],
            key=lambda c: (
                0 if c.tipo == 'urgente' else 1,
                0 if c.es_prioritario else 1,
                -(c.fecha_publicacion.timestamp() if c.fecha_publicacion else 0),
            ),
        )[:4]

        counts_by_tipo: Dict[str, int] = {}
        for c in items:
            counts_by_tipo[c.tipo] = counts_by_tipo.get(c.tipo, 0) + 1

        return {
            'com_stats': {
                'total': total,
                'urgentes': urgentes,
                'citaciones': citaciones,
                'eventos': eventos,
                'prioritarios': prioritarios,
                'confirmacion': confirmacion,
                'destacados': destacados,
            },
            'com_alertas': alertas,
            'com_prioridad': prioridad,
            'com_proximos_eventos': proximos,
            'com_counts_tipo': counts_by_tipo,
        }

    @staticmethod
    def get_staff_comunicados_list_context(
        comunicados,
        *,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Métricas e inteligencia para lista premium de funcionarios (admin escolar, etc.).
        """
        from datetime import timedelta
        from django.utils import timezone

        ctx = ComunicadosService.get_profesor_comunicados_list_context(comunicados)
        items = list(comunicados)
        now = timezone.now()
        semana_inicio = now - timedelta(days=7)
        publicados_semana = sum(
            1 for c in items
            if getattr(c, 'fecha_publicacion', None) and c.fecha_publicacion >= semana_inicio
        )
        ctx['com_stats']['publicados_semana'] = publicados_semana

        if is_admin:
            alertas = []
            total = ctx['com_stats']['total']
            urgentes = ctx['com_stats']['urgentes']
            confirmacion = ctx['com_stats']['confirmacion']
            citaciones = ctx['com_stats']['citaciones']
            proximos = ctx.get('com_proximos_eventos') or []

            if total == 0:
                alertas.append(
                    'Aún no hay comunicados publicados. Usa «Nuevo comunicado» para la primera circular.'
                )
            if publicados_semana:
                alertas.append(
                    f'{publicados_semana} publicado{"s" if publicados_semana != 1 else ""} '
                    f'en los últimos 7 días.'
                )
            if urgentes:
                alertas.append(
                    f'{urgentes} marcado{"s" if urgentes != 1 else ""} como urgente o prioritario.'
                )
            if confirmacion:
                alertas.append(
                    f'{confirmacion} requiere{"n" if confirmacion != 1 else ""} '
                    f'confirmación de lectura — revisa estadísticas tras publicar.'
                )
            if citaciones:
                alertas.append(
                    f'{citaciones} citación{"es" if citaciones != 1 else ""} '
                    f'con posible fecha de reunión.'
                )
            if proximos:
                alertas.append(
                    f'{len(proximos)} evento{"s" if len(proximos) != 1 else ""} '
                    f'programado{"s" if len(proximos) != 1 else ""} próximamente.'
                )
            ctx['com_alertas'] = alertas[:5]
            ctx['com_guide_title'] = 'Centro de comunicaciones'
            ctx['com_guide_text'] = (
                'Gestiona circulares, citaciones y avisos del establecimiento. '
                'Los indicadores consideran todo el historial; el listado respeta el filtro activo.'
            )
        else:
            ctx['com_guide_title'] = 'Bandeja institucional'
            ctx['com_guide_text'] = (
                'Circulares, citaciones y avisos oficiales. '
                'Los contadores reflejan tu bandeja completa; el listado respeta el filtro de tipo.'
            )

        return ctx

    @staticmethod
    def _get_leidos_ids_for_user(user, comunicado_ids) -> set:
        from ..models import ConfirmacionLectura

        if not comunicado_ids:
            return set()
        return set(
            ConfirmacionLectura.objects.filter(
                usuario=user,
                comunicado_id__in=comunicado_ids,
                leido=True,
            ).values_list('comunicado_id', flat=True)
        )

    @staticmethod
    def get_alumno_comunicados_context(user, query_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Contexto para la lista de comunicados del estudiante: métricas, secciones y filtros.
        """
        query_params = query_params or {}
        tipo_filtro = (query_params.get('tipo') or '').strip()
        estado_filtro = (query_params.get('estado') or '').strip()
        busqueda = (query_params.get('q') or '').strip()

        comunicados_qs = ComunicadosService.get_comunicados_for_user(user)
        comunicados_tipo = ComunicadosService.filter_comunicados_by_type(comunicados_qs, tipo_filtro)
        comunicados_list = list(comunicados_tipo)
        comunicado_ids = [c.id_comunicado for c in comunicados_list]
        leidos_ids = ComunicadosService._get_leidos_ids_for_user(user, comunicado_ids)

        def _item_dict(comunicado):
            esta_leido = comunicado.id_comunicado in leidos_ids
            return {
                'comunicado': comunicado,
                'esta_leido': esta_leido,
                'es_urgente': ComunicadosService._comunicado_es_urgente(comunicado),
            }

        todos_items = [_item_dict(c) for c in comunicados_list]

        sin_leer_total = sum(1 for i in todos_items if not i['esta_leido'])
        leidos_total = sum(1 for i in todos_items if i['esta_leido'])
        urgentes_total = sum(1 for i in todos_items if i['es_urgente'])
        total = len(todos_items)

        items_filtrados = todos_items
        if estado_filtro == 'sin_leer':
            items_filtrados = [i for i in items_filtrados if not i['esta_leido']]
        elif estado_filtro == 'leidos':
            items_filtrados = [i for i in items_filtrados if i['esta_leido']]

        if busqueda:
            q_lower = busqueda.lower()
            items_filtrados = [
                i for i in items_filtrados
                if q_lower in i['comunicado'].titulo.lower()
                or q_lower in (i['comunicado'].contenido or '').lower()
            ]

        usar_secciones = not estado_filtro and not busqueda
        comunicados_prioritarios = []
        comunicados_sin_leer = []
        comunicados_leidos = []

        if usar_secciones:
            for item in items_filtrados:
                if item['esta_leido']:
                    comunicados_leidos.append(item)
                elif item['es_urgente']:
                    comunicados_prioritarios.append(item)
                else:
                    comunicados_sin_leer.append(item)
        else:
            comunicados_filtrados = items_filtrados

        filtros_activos = bool(tipo_filtro or estado_filtro or busqueda)
        todo_leido = total > 0 and sin_leer_total == 0

        eventos_proximos = sorted(
            [i for i in todos_items if i['comunicado'].fecha_evento],
            key=lambda i: i['comunicado'].fecha_evento,
        )[:5]

        hero_subtitle = 'Información oficial, circulares y avisos del colegio'
        if sin_leer_total:
            hero_subtitle = f'Tienes {sin_leer_total} comunicado(s) pendiente(s) de revisar'

        return {
            'hero_subtitle_comunicados': hero_subtitle,
            'eventos_proximos': eventos_proximos,
            'comunicados_stats': {
                'sin_leer': sin_leer_total,
                'leidos': leidos_total,
                'urgentes': urgentes_total,
                'total': total,
            },
            'sin_leer_count': sin_leer_total,
            'leidos_count': leidos_total,
            'urgentes_count': urgentes_total,
            'total_comunicados': total,
            'tipo_filtro': tipo_filtro,
            'estado_filtro': estado_filtro,
            'busqueda': busqueda,
            'filtros_activos': filtros_activos,
            'usar_secciones': usar_secciones,
            'todo_leido': todo_leido,
            'comunicados_prioritarios': comunicados_prioritarios,
            'comunicados_sin_leer': comunicados_sin_leer,
            'comunicados_leidos': comunicados_leidos,
            'comunicados_filtrados': items_filtrados if not usar_secciones else [],
            'tiene_comunicados': total > 0,
            'hay_resultados': len(items_filtrados) > 0,
        }

    @staticmethod
    def mark_comunicados_as_read_for_user(user, comunicados):
        """
        Marca comunicados como leídos para un usuario (si requieren confirmación)

        Args:
            user: Usuario
            comunicados: QuerySet de comunicados
        """
        from ..models import ConfirmacionLectura

        if PolicyService.has_capability(
            user,
            'SYSTEM_CONFIGURE',
            school_id=getattr(user, 'rbd_colegio', None),
        ):
            return  # Admins no necesitan marcar como leídos

        for comunicado in comunicados:
            if comunicado.requiere_confirmacion:
                ConfirmacionLectura.objects.get_or_create(
                    comunicado=comunicado,
                    usuario=user
                )

    @staticmethod
    def can_user_view_comunicado(user, comunicado) -> bool:
        """
        Verifica si un usuario puede ver un comunicado específico

        Args:
            user: Usuario
            comunicado: Instancia de Comunicado

        Returns:
            bool: True si puede ver el comunicado
        """
        # Verificar que pertenezca al mismo colegio
        if comunicado.colegio != user.colegio:
            return False

        # Si es admin escolar, puede ver todos
        if ComunicadosService._is_school_admin(user):
            return True

        # Para otros roles, aplicar filtros similares a get_comunicados_for_user
        from backend.apps.accounts.models import PerfilEstudiante

        if ComunicadosService._is_teacher(user):
            return comunicado.destinatario in ['todos', 'profesores']
        elif ComunicadosService._is_student(user):
            if comunicado.destinatario in ['todos', 'estudiantes', 'apoderados']:
                return True
            elif comunicado.destinatario == 'curso_especifico':
                try:
                    perfil = PerfilEstudiante.objects.get(user=user)
                    if perfil.curso_actual:
                        return comunicado.cursos_destinatarios.filter(id_curso=perfil.curso_actual.id_curso).exists()
                    return False
                except PerfilEstudiante.DoesNotExist:
                    return False

        return comunicado.destinatario == 'todos'

    @staticmethod
    def create_comunicado(user, data: Dict, files: Dict) -> Dict:
        return ComunicadosService.execute('create_comunicado', {
            'user': user,
            'data': data,
            'files': files,
        })

    @staticmethod
    def _execute_create_comunicado(params: Dict[str, Any]) -> Dict:
        """
        Crea un nuevo comunicado

        Args:
            user: Usuario que crea el comunicado
            data: Datos del formulario POST
            files: Archivos del request

        Returns:
            Dict: {'success': bool, 'message': str, 'comunicado': Comunicado or None}
        
        Raises:
            PrerequisiteException: Si el colegio no tiene ciclo activo o datos inválidos
        """
        from ..models import Comunicado, AdjuntoComunicado
        from backend.apps.cursos.models import Curso
        from backend.apps.institucion.models import CicloAcademico

        user = params['user']
        data = params['data']
        files = params['files']

        try:
            # Validar permisos
            is_valid, error_msg = CommonValidations.validate_admin_permissions(user)
            if not is_valid:
                return {'success': False, 'message': error_msg, 'comunicado': None}

            IntegrityService.validate_school_integrity_or_raise(
                school_id=user.colegio.rbd,
                action='CREATE_COMUNICADO',
            )
            
            # VALIDACIÓN DEFENSIVA: Verificar que el colegio tiene ciclo activo
            ciclo_activo = CicloAcademico.objects.filter(colegio=user.colegio, estado='ACTIVO').first()
            if not ciclo_activo:
                raise PrerequisiteException(
                    error_type='MISSING_CICLO_ACTIVO',
                    user_message=f'El colegio {user.colegio.nombre} no tiene un ciclo académico activo. Debe crear uno antes de publicar comunicados.',
                    action_url='/admin/institucion/cicloacademico/add/',
                    context={'rbd_colegio': user.colegio.rbd, 'colegio_nombre': user.colegio.nombre}
                )
            
            # VALIDACIÓN DEFENSIVA: Verificar que usuario esté activo
            if not user.is_active:
                raise PrerequisiteException(
                    error_type='INVALID_STATE',
                    user_message='No puedes publicar comunicados: tu cuenta está inactiva',
                    context={'user_id': user.id}
                )

            # Extraer datos
            tipo = data.get('tipo')
            titulo = data.get('titulo')
            contenido = data.get('contenido')
            destinatario = data.get('destinatario')
            archivo_adjunto = files.get('archivo_adjunto')

            fecha_evento_str = data.get('fecha_evento')
            lugar_evento = data.get('lugar_evento')
            requiere_confirmacion = data.get('requiere_confirmacion') == 'on'
            es_prioritario = data.get('es_prioritario') == 'on'
            es_destacado = data.get('es_destacado') == 'on'

            # Parsear fecha si existe
            fecha_evento = None
            if fecha_evento_str:
                try:
                    fecha_evento = datetime.strptime(fecha_evento_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    return {'success': False, 'message': 'Formato de fecha inválido', 'comunicado': None}

            # Crear comunicado
            comunicado = Comunicado.objects.create(
                colegio=user.colegio,
                tipo=tipo,
                titulo=titulo,
                contenido=contenido,
                destinatario=destinatario,
                archivo_adjunto=archivo_adjunto,
                fecha_evento=fecha_evento,
                lugar_evento=lugar_evento,
                requiere_confirmacion=requiere_confirmacion,
                es_prioritario=es_prioritario,
                es_destacado=es_destacado,
                publicado_por=user
            )

            # Asignar cursos si es específico
            if destinatario == 'curso_especifico':
                cursos_ids = data.getlist('cursos')
                if not cursos_ids:
                    comunicado.delete()
                    return {
                        'success': False,
                        'message': 'Debe seleccionar al menos un curso destinatario.',
                        'comunicado': None
                    }

                cursos = Curso.objects.filter(
                    id_curso__in=cursos_ids,
                    colegio=user.colegio,
                    activo=True,
                    ciclo_academico__estado='ACTIVO'
                )
                if cursos.count() != len(cursos_ids):
                    comunicado.delete()
                    return {
                        'success': False,
                        'message': 'Uno o más cursos no son válidos para este comunicado.',
                        'comunicado': None
                    }

                comunicado.cursos_destinatarios.set(cursos)

            # Procesar archivos adicionales
            archivos_adicionales = files.getlist('archivos_adicionales')
            for archivo in archivos_adicionales:
                AdjuntoComunicado.objects.create(
                    comunicado=comunicado,
                    archivo=archivo,
                    nombre_archivo=archivo.name,
                    tamanio_bytes=archivo.size,
                    tipo_mime=archivo.content_type
                )

            user_label = user.get_full_name() or getattr(user, 'email', None) or f"id:{user.id}"
            logger.info(f"Comunicado creado - Usuario: {user_label}, Título: {titulo}")
            return {
                'success': True,
                'message': f'✓ Comunicado "{titulo}" publicado exitosamente.',
                'comunicado': comunicado
            }

        except Exception as e:
            user_label = user.get_full_name() or getattr(user, 'email', None) or f"id:{user.id}"
            logger.error(f"Error creando comunicado - Usuario: {user_label}, Error: {str(e)}")
            return {
                'success': False,
                'message': f'Error al crear comunicado: {str(e)}',
                'comunicado': None
            }

    @staticmethod
    def mark_comunicado_as_read(user, comunicado):
        """
        Marca un comunicado como leído para un usuario

        Args:
            user: Usuario
            comunicado: Instancia de Comunicado
        """
        from ..models import ConfirmacionLectura

        if PolicyService.has_capability(
            user,
            'SYSTEM_CONFIGURE',
            school_id=getattr(user, 'rbd_colegio', None),
        ):
            return  # Admins no marcan como leídos

        conf, created = ConfirmacionLectura.objects.get_or_create(
            comunicado=comunicado,
            usuario=user,
        )
        conf.marcar_como_leido()

    @staticmethod
    def confirm_attendance_to_comunicado(user, comunicado) -> bool:
        """
        Confirma asistencia a un evento/comunicado

        Args:
            user: Usuario
            comunicado: Instancia de Comunicado

        Returns:
            bool: True si se confirmó correctamente
        """
        from ..models import ConfirmacionLectura

        if not comunicado.requiere_confirmacion:
            return False

        conf, created = ConfirmacionLectura.objects.get_or_create(
            comunicado=comunicado,
            usuario=user
        )
        conf.confirmar_asistencia()
        return True

    @staticmethod
    def get_comunicado_statistics(user, comunicado) -> Dict:
        """
        Obtiene estadísticas de un comunicado

        Args:
            user: Usuario (debe ser admin)
            comunicado: Instancia de Comunicado

        Returns:
            Dict: Estadísticas del comunicado
        """
        from ..models import ConfirmacionLectura

        # Validar permisos
        is_valid, error_msg = CommonValidations.validate_admin_permissions(user)
        if not is_valid:
            return {'error': error_msg}

        # Verificar propiedad del comunicado
        if comunicado.colegio != user.colegio:
            return {'error': 'No tienes permiso para ver este comunicado'}

        # Obtener confirmaciones
        confirmaciones = ConfirmacionLectura.objects.filter(comunicado=comunicado)

        stats = {
            'total': confirmaciones.count(),
            'leidos': confirmaciones.filter(leido=True).count(),
            'confirmados': confirmaciones.filter(confirmado=True).count(),
            'pendientes': confirmaciones.filter(leido=False).count(),
        }

        return {
            'comunicado': comunicado,
            'confirmaciones': confirmaciones.select_related('usuario'),
            'stats': stats,
        }

    @staticmethod
    def get_user_confirmacion_for_comunicado(user, comunicado) -> Optional[Any]:
        """
        Obtiene la confirmación de lectura de un usuario para un comunicado específico

        Args:
            user: Usuario de Django
            comunicado: Instancia del modelo Comunicado

        Returns:
            ConfirmacionLectura or None: La confirmación del usuario o None si no existe
        """
        from ..models import ConfirmacionLectura

        if PolicyService.has_capability(
            user,
            'SYSTEM_CONFIGURE',
            school_id=getattr(user, 'rbd_colegio', None),
        ):
            return None

        try:
            return ConfirmacionLectura.objects.get(
                comunicado=comunicado,
                usuario=user
            )
        except ConfirmacionLectura.DoesNotExist:
            return None

    @staticmethod
    def get_detailed_statistics(user, comunicado_id):
        """
        Obtiene estadísticas detalladas para dashboard de estadísticas.
        """
        from django.shortcuts import get_object_or_404

    @staticmethod
    def notify_new_comunicado(comunicado) -> None:
        """Gestiona notificaciones/confirmaciones para un comunicado recién creado."""
        from backend.apps.accounts.models import PerfilEstudiante, User
        from backend.apps.cursos.models import Curso
        from backend.apps.notificaciones.models import Notificacion
        from ..models import ConfirmacionLectura

        destinatarios = []

        if comunicado.destinatario == 'todos':
            destinatarios = User.objects.filter(
                rbd_colegio=comunicado.colegio.rbd,
                is_active=True
            ).exclude(id=comunicado.publicado_por.id)

        elif comunicado.destinatario == 'profesores':
            destinatarios = User.objects.filter(
                rbd_colegio=comunicado.colegio.rbd,
                perfil_profesor__isnull=False,
                is_active=True
            )

        elif comunicado.destinatario == 'estudiantes':
            destinatarios = User.objects.filter(
                rbd_colegio=comunicado.colegio.rbd,
                perfil_estudiante__isnull=False,
                is_active=True
            )

        elif comunicado.destinatario == 'apoderados':
            destinatarios = User.objects.filter(
                rbd_colegio=comunicado.colegio.rbd,
                perfil_apoderado__isnull=False,
                is_active=True
            )

        elif comunicado.destinatario == 'curso_especifico':
            cursos_ids = comunicado.cursos_destinatarios.values_list('id_curso', flat=True)
            ciclos_ids = Curso.objects.filter(id_curso__in=cursos_ids).values_list('ciclo_academico', flat=True)
            perfiles = PerfilEstudiante.objects.filter(
                user__rbd_colegio=comunicado.colegio.rbd,
                ciclo_actual__in=ciclos_ids,
                estado_academico='Activo'
            ).select_related('user')
            destinatarios = [perfil.user for perfil in perfiles]

        tipo_notif = {
            'comunicado': 'comunicado_nuevo',
            'evento': 'evento_nuevo',
            'citacion': 'citacion_nueva',
            'noticia': 'noticia_nueva',
            'urgente': 'urgente',
        }.get(comunicado.tipo, 'comunicado_nuevo')

        icono = comunicado.get_tipo_display().split()[0]

        for usuario in destinatarios:
            Notificacion.objects.create(
                destinatario=usuario,
                tipo=tipo_notif,
                titulo=f"{icono} {comunicado.titulo}",
                mensaje=comunicado.contenido[:200],
                enlace=f'/comunicados/{comunicado.id_comunicado}/',
                prioridad='normal' if not comunicado.es_prioritario else 'alta'
            )

            if comunicado.requiere_confirmacion:
                ConfirmacionLectura.objects.get_or_create(
                    comunicado=comunicado,
                    usuario=usuario
                )


    @staticmethod
    def get_plantillas_for_colegio(user):
        """
        Obtiene plantillas agrupadas por categoría para el colegio del usuario.
        """
        from ..models import PlantillaComunicado

        plantillas = PlantillaComunicado.objects.filter(
            colegio=user.colegio,
            activa=True
        ).order_by('categoria', '-veces_usada')

        # Agrupar por categoría
        plantillas_por_categoria = {}
        for plantilla in plantillas:
            cat = plantilla.get_categoria_display()
            if cat not in plantillas_por_categoria:
                plantillas_por_categoria[cat] = []
            plantillas_por_categoria[cat].append(plantilla)

        return {
            'plantillas': plantillas,
            'plantillas_por_categoria': plantillas_por_categoria,
            'total_plantillas': plantillas.count(),
        }

    @staticmethod
    def get_plantilla_creation_form_context():
        """Obtiene metadata para formulario de creación de plantilla."""
        from ..models import Comunicado, PlantillaComunicado

        return {
            'categorias': PlantillaComunicado.CATEGORIAS,
            'tipos': Comunicado.TIPOS,
            'destinatarios': Comunicado.DESTINATARIOS,
            'variables_disponibles': PlantillaComunicado().get_variables_disponibles(),
        }

    @staticmethod
    def get_plantilla_edit_form_context(plantilla):
        """Obtiene metadata para formulario de edición de plantilla."""
        from ..models import Comunicado, PlantillaComunicado

        return {
            'plantilla': plantilla,
            'categorias': PlantillaComunicado.CATEGORIAS,
            'tipos': Comunicado.TIPOS,
            'destinatarios': Comunicado.DESTINATARIOS,
            'variables_disponibles': plantilla.get_variables_disponibles(),
        }

    @staticmethod
    def crear_plantilla(user, data: Dict):
        """
        Crea una nueva plantilla de comunicado.
        """
        from ..models import PlantillaComunicado

        plantilla = PlantillaComunicado.objects.create(
            colegio=user.colegio,
            nombre=data['nombre'],
            categoria=data['categoria'],
            descripcion=data.get('descripcion', ''),
            titulo_plantilla=data['titulo_plantilla'],
            contenido_plantilla=data['contenido_plantilla'],
            tipo_default=data.get('tipo_default', 'comunicado'),
            destinatario_default=data.get('destinatario_default', 'todos'),
            requiere_confirmacion_default=data.get('requiere_confirmacion') == 'on',
            es_prioritario_default=data.get('es_prioritario') == 'on',
            creada_por=user
        )
        return plantilla

    @staticmethod
    def actualizar_plantilla(user, plantilla_id, data: Dict):
        """
        Actualiza una plantilla existente.
        """
        from django.shortcuts import get_object_or_404
        from ..models import PlantillaComunicado

        plantilla = get_object_or_404(PlantillaComunicado, id_plantilla=plantilla_id)
        if plantilla.colegio != user.colegio:
            raise PermissionError('No tienes permiso para editar esta plantilla')

        plantilla.nombre = data['nombre']
        plantilla.categoria = data['categoria']
        plantilla.descripcion = data.get('descripcion', '')
        plantilla.titulo_plantilla = data['titulo_plantilla']
        plantilla.contenido_plantilla = data['contenido_plantilla']
        plantilla.tipo_default = data['tipo_default']
        plantilla.destinatario_default = data['destinatario_default']
        plantilla.requiere_confirmacion_default = data.get('requiere_confirmacion') == 'on'
        plantilla.es_prioritario_default = data.get('es_prioritario') == 'on'
        plantilla.save()
        return plantilla

    @staticmethod
    def eliminar_plantilla(user, plantilla_id):
        """
        Desactiva una plantilla (soft delete).
        """
        from django.shortcuts import get_object_or_404
        from ..models import PlantillaComunicado

        plantilla = get_object_or_404(PlantillaComunicado, id_plantilla=plantilla_id)
        if plantilla.colegio != user.colegio:
            raise PermissionError('No tienes permiso para eliminar esta plantilla')

        plantilla.activa = False
        plantilla.save()
        return plantilla

    @staticmethod
    def get_active_courses_for_user(user):
        """Obtiene cursos activos del colegio del usuario."""
        from backend.apps.cursos.models import Curso

        return Curso.objects.filter(colegio=user.colegio, activo=True)

    @staticmethod
    def get_massive_confirmations_context(user, comunicado, filtro: str = 'todos', recalcular: bool = False):
        """
        Construye contexto de confirmaciones masivas para un comunicado.
        """
        from ..models import ConfirmacionLectura, EstadisticaComunicado

        estadisticas, created = EstadisticaComunicado.objects.get_or_create(
            comunicado=comunicado
        )
        if created or recalcular:
            estadisticas.calcular_estadisticas()

        confirmaciones_all = ConfirmacionLectura.objects.filter(
            comunicado=comunicado
        ).select_related('usuario', 'usuario__role').order_by('-fecha_lectura', 'usuario__first_name')

        if filtro == 'leidos':
            confirmaciones = confirmaciones_all.filter(leido=True)
        elif filtro == 'pendientes':
            confirmaciones = confirmaciones_all.filter(leido=False)
        elif filtro == 'confirmados':
            confirmaciones = confirmaciones_all.filter(confirmado=True)
        else:
            confirmaciones = confirmaciones_all

        confirmaciones_lista = list(confirmaciones)
        confirmaciones_por_rol = {
            'profesores': [],
            'estudiantes': [],
            'apoderados': [],
        }
        for item in confirmaciones_lista:
            if ComunicadosService._has_profile(item.usuario, 'perfil_profesor'):
                confirmaciones_por_rol['profesores'].append(item)
            elif ComunicadosService._has_profile(item.usuario, 'perfil_estudiante'):
                confirmaciones_por_rol['estudiantes'].append(item)
            elif ComunicadosService._has_profile(item.usuario, 'perfil_apoderado'):
                confirmaciones_por_rol['apoderados'].append(item)

        return {
            'estadisticas': estadisticas,
            'confirmaciones': confirmaciones_lista,
            'confirmaciones_por_rol': confirmaciones_por_rol,
            'total_confirmaciones': confirmaciones_all.count(),
        }

    @staticmethod
    def send_massive_reminders(user, comunicado) -> int:
        """
        Crea notificaciones de recordatorio para usuarios pendientes.
        """
        from ..models import ConfirmacionLectura
        from backend.apps.notificaciones.models import Notificacion
        from backend.apps.notificaciones.services.dispatch_service import NotificationDispatchService

        confirmaciones_pendientes = ConfirmacionLectura.objects.filter(
            comunicado=comunicado,
            leido=False
        ).select_related('usuario')

        notificaciones = [
            Notificacion(
                destinatario=confirmacion.usuario,
                tipo='comunicado_nuevo',
                titulo=f'Recordatorio: {comunicado.titulo}',
                mensaje=(
                    'Te recordamos que tienes un comunicado pendiente de lectura. '
                    f'Por favor, revisa: {comunicado.titulo[:100]}'
                ),
                enlace=f'/comunicados/{comunicado.id_comunicado}/',
                prioridad='normal' if not comunicado.es_prioritario else 'alta'
            )
            for confirmacion in confirmaciones_pendientes
        ]

        if notificaciones:
            created_notifications = Notificacion.objects.bulk_create(notificaciones)
            NotificationDispatchService.dispatch_bulk(created_notifications)

        return len(notificaciones)

    @staticmethod
    def get_plantilla_for_user(user, plantilla_id):
        """Obtiene plantilla validando pertenencia al colegio."""
        from django.shortcuts import get_object_or_404
        from ..models import PlantillaComunicado

        plantilla = get_object_or_404(PlantillaComunicado, id_plantilla=plantilla_id)
        if plantilla.colegio != user.colegio:
            raise PermissionError('No tienes permiso para usar esta plantilla')
        return plantilla

    @staticmethod
    def get_active_plantilla_for_user(user, plantilla_id):
        """Obtiene plantilla activa validando pertenencia al colegio."""
        from django.shortcuts import get_object_or_404
        from ..models import PlantillaComunicado

        plantilla = get_object_or_404(
            PlantillaComunicado,
            id_plantilla=plantilla_id,
            activa=True
        )
        if plantilla.colegio != user.colegio:
            raise PermissionError('No tienes permiso para usar esta plantilla')
        return plantilla

    @staticmethod
    def create_comunicado_from_template(user, plantilla, data: Dict[str, Any]):
        """
        Crea comunicado desde una plantilla y contexto de variables.
        """
        from ..models import Comunicado

        contexto = {}
        for key in data:
            if key.startswith('var_'):
                contexto[key[4:]] = data[key]

        titulo, contenido = plantilla.renderizar(contexto)

        comunicado = Comunicado.objects.create(
            colegio=user.colegio,
            tipo=data.get('tipo', plantilla.tipo_default),
            titulo=titulo,
            contenido=contenido,
            destinatario=data.get('destinatario', plantilla.destinatario_default),
            requiere_confirmacion=data.get('requiere_confirmacion') == 'on',
            es_prioritario=data.get('es_prioritario') == 'on',
            publicado_por=user
        )

        plantilla.incrementar_contador_uso()
        return comunicado

    @staticmethod
    def get_template_usage_context(user, plantilla):
        """Obtiene contexto de formulario para usar plantilla."""
        import re
        from ..models import Comunicado

        variables_encontradas = set()
        for match in re.finditer(
            r'\{\{(\w+)\}\}',
            plantilla.titulo_plantilla + plantilla.contenido_plantilla
        ):
            variables_encontradas.add(match.group(1))

        return {
            'plantilla': plantilla,
            'variables': sorted(variables_encontradas),
            'tipos': Comunicado.TIPOS,
            'destinatarios': Comunicado.DESTINATARIOS,
            'cursos': ComunicadosService.get_active_courses_for_user(user),
        }
