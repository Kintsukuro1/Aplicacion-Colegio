"""
MensajeriaService - Servicio para gestión de mensajería y conversaciones

Este servicio centraliza la lógica de negocio para:
- Verificar acceso a clases y conversaciones
- Crear y gestionar conversaciones
- Enviar y recibir mensajes
- Marcar mensajes como leídos
- Obtener datos de bandeja de mensajes
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from django.db.models import Q
from django.utils import timezone

from backend.common.validations import CommonValidations
from backend.common.services import PermissionService
from backend.common.exceptions import PrerequisiteException
from backend.common.utils.error_response import ErrorResponseBuilder
from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.mensajeria.models import Mensaje

logger = logging.getLogger('mensajeria')


class MensajeriaService:
    """
    Servicio para gestión completa de mensajería
    """

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        MensajeriaService.validate(operation, params)
        return MensajeriaService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(MensajeriaService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')

    @staticmethod
    def get_class_for_messages(clase_id):
        from backend.apps.cursos.models import Clase

        return Clase.objects.select_related('curso', 'asignatura', 'profesor').get(id=clase_id)

    @staticmethod
    def get_user_for_messages(user_id):
        from backend.apps.accounts.models import User

        return User.objects.get(id=user_id)

    @staticmethod
    def user_has_access_to_class(user, clase) -> bool:
        """
        Verifica si un usuario tiene acceso a una clase específica

        Args:
            user: Usuario de Django
            clase: Instancia del modelo Clase

        Returns:
            bool: True si tiene acceso
        """
        from backend.apps.accounts.models import PerfilEstudiante

        # Si es profesor de la clase
        if clase.profesor_id == user.id:
            return True

        if hasattr(user, 'perfil_apoderado'):
            # Fix: apoderado puede abrir chat en clases donde tiene pupilos matriculados.
            from backend.apps.cursos.models import ClaseEstudiante

            return ClaseEstudiante.objects.filter(
                clase=clase,
                activo=True,
                estudiante__apoderados__user=user,
            ).exists()

        from backend.apps.cursos.models import ClaseEstudiante

        if ClaseEstudiante.objects.filter(
            clase=clase,
            estudiante=user,
            activo=True,
        ).exists():
            return True

        perfil = PerfilEstudiante.objects.filter(user=user).first()
        if not perfil:
            return False

        return (
            perfil.estado_academico == 'Activo'
            and perfil.ciclo_actual is not None
            and clase.curso.ciclo_academico == perfil.ciclo_actual
        )

    @staticmethod
    def get_or_create_conversacion(clase, u1, u2) -> Any:
        """
        Obtiene o crea una conversación entre dos usuarios en una clase

        Args:
            clase: Instancia del modelo Clase
            u1: Primer usuario
            u2: Segundo usuario

        Returns:
            Conversacion: La conversación creada o existente
        
        Raises:
            PrerequisiteException: Si la clase está inactiva o usuarios inactivos
        """
        from ..models import Conversacion

        IntegrityService.validate_school_integrity_or_raise(
            school_id=clase.colegio.rbd,
            action='GET_OR_CREATE_CONVERSACION',
        )
        
        # VALIDACIÓN DEFENSIVA: Verificar que la clase esté activa
        if not clase.activo:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                user_message=f'No se pueden crear conversaciones en la clase {clase.asignatura.nombre}: la clase está inactiva',
                context={'clase_id': clase.id_clase}
            )
        
        # VALIDACIÓN DEFENSIVA: Verificar que los usuarios estén activos
        if not u1.is_active:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                user_message=f'No se puede crear conversación: el usuario {u1.email} está inactivo',
                context={'user_id': u1.id}
            )
        
        if not u2.is_active:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                user_message=f'No se puede crear conversación: el usuario {u2.email} está inactivo',
                context={'user_id': u2.id}
            )

        # VALIDACIÓN DEFENSIVA: Verificar pertenencia al colegio de la clase
        if u1.rbd_colegio != clase.colegio.rbd or u2.rbd_colegio != clase.colegio.rbd:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                user_message='Los participantes no pertenecen al colegio de la clase',
                context={
                    'clase_id': clase.id_clase,
                    'colegio_rbd': clase.colegio.rbd,
                    'u1_rbd': u1.rbd_colegio,
                    'u2_rbd': u2.rbd_colegio,
                }
            )

        # VALIDACIÓN DEFENSIVA: Verificar acceso de ambos usuarios a la clase
        if not MensajeriaService.user_has_access_to_class(u1, clase) or not MensajeriaService.user_has_access_to_class(u2, clase):
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                user_message='Uno o ambos participantes no tienen acceso válido a la clase',
                context={'clase_id': clase.id_clase, 'u1_id': u1.id, 'u2_id': u2.id}
            )

        # Normalizar orden de participantes para unicidad
        if u1.id < u2.id:
            p1, p2 = u1, u2
        else:
            p1, p2 = u2, u1

        conversacion, created = Conversacion.objects.get_or_create(
            clase=clase,
            participante1=p1,
            participante2=p2,
            defaults={'ultima_actividad': timezone.now()},
        )

        if not created and conversacion.ultima_actividad is None:
            conversacion.ultima_actividad = timezone.now()
            conversacion.save(update_fields=['ultima_actividad'])

        return conversacion

    @staticmethod
    def get_conversaciones_data(user) -> List[Dict[str, Any]]:
        """
        Obtiene los datos de conversaciones para la bandeja de mensajes

        Args:
            user: Usuario de Django

        Returns:
            List: Lista de diccionarios con datos de conversaciones
        """
        from ..models import Conversacion

        conversaciones = (
            Conversacion.objects.filter(Q(participante1=user) | Q(participante2=user))
            .select_related('clase', 'clase__asignatura', 'clase__curso', 'participante1', 'participante2')
            .prefetch_related('mensajes')
            .order_by('-ultima_actividad')
        )

        data = []
        for conv in conversaciones:
            otro = conv.get_otro_participante(user)
            ultimo = conv.mensajes.order_by('-fecha_envio').first()
            no_leidos = conv.mensajes.filter(receptor=user, leido=False).count()
            data.append(
                {
                    'conversacion': conv,
                    'destinatario': otro,
                    'ultimo_mensaje': ultimo,
                    'no_leidos': no_leidos,
                }
            )
        return data

    @staticmethod
    def get_clase_mensajes_panel_context(user, clase) -> Dict[str, Any]:
        """Contactos y conversaciones de una clase para el panel en detalle (sin iframe)."""
        from django.urls import reverse

        from backend.apps.accounts.models import User as UserModel
        from backend.apps.cursos.models import ClaseEstudiante

        conversaciones_clase = []
        conv_por_estudiante: Dict[int, Dict[str, Any]] = {}
        for item in MensajeriaService.get_conversaciones_data(user):
            if item['conversacion'].clase_id != clase.id:
                continue
            conversaciones_clase.append(item)
            otro = item['destinatario']
            if otro.id != user.id:
                conv_por_estudiante[otro.id] = item

        estudiante_ids = list(
            ClaseEstudiante.objects.filter(clase=clase, activo=True).values_list(
                'estudiante_id', flat=True
            )
        )
        estudiantes = (
            UserModel.objects.filter(id__in=estudiante_ids, is_active=True)
            .order_by('apellido_paterno', 'apellido_materno', 'nombre')
        )

        contactos = []
        for estudiante in estudiantes:
            conv_item = conv_por_estudiante.get(estudiante.id)
            ultimo = conv_item['ultimo_mensaje'] if conv_item else None
            preview = ''
            if ultimo and ultimo.contenido:
                preview = ultimo.contenido[:100]
            contactos.append({
                'estudiante': estudiante,
                'conversacion_id': (
                    conv_item['conversacion'].id_conversacion if conv_item else None
                ),
                'no_leidos': conv_item['no_leidos'] if conv_item else 0,
                'ultimo_preview': preview,
                'tiene_conversacion': conv_item is not None,
            })

        no_leidos = sum(item['no_leidos'] for item in conversaciones_clase)
        sin_conversar = sum(1 for c in contactos if not c['tiene_conversacion'])

        return {
            'mensajes_clase_contactos': contactos,
            'mensajes_clase_conversaciones': conversaciones_clase,
            'mensajes_clase_no_leidos': no_leidos,
            'mensajes_clase_sin_conversar': sin_conversar,
            'mensajes_bandeja_url': (
                f"{reverse('mensajeria:bandeja_mensajes')}?clase_id={clase.id}"
            ),
        }

    @staticmethod
    def _build_mensajeria_inteligencia(
        enriched: List[Dict[str, Any]],
        clases: Optional[List[Any]],
        no_leidos_total: int,
        notificaciones_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Sugerencias y contactos docentes para la bandeja MM."""
        conv_por_clase: Dict[int, Dict[str, Any]] = {}
        for item in enriched:
            if not item.get('con_profesor'):
                continue
            conv_por_clase[item['conversacion'].clase_id] = item

        profesores_contacto: List[Dict[str, Any]] = []
        clases_sin_conversar = 0
        for clase in clases or []:
            if not getattr(clase, 'profesor_id', None) or not clase.profesor_id:
                continue
            existente = conv_por_clase.get(clase.id)
            tiene_conversacion = bool(existente)
            if not tiene_conversacion:
                clases_sin_conversar += 1
            ultimo = existente['ultimo_mensaje'] if existente else None
            preview = ''
            if ultimo and getattr(ultimo, 'contenido', None):
                preview = (ultimo.contenido or '')[:100]
            asignatura = clase.asignatura.nombre if getattr(clase, 'asignatura_id', None) else 'Clase'
            asignatura_color = ''
            if getattr(clase, 'asignatura_id', None) and getattr(clase.asignatura, 'color', None):
                asignatura_color = clase.asignatura.color
            profesores_contacto.append({
                'clase': clase,
                'profesor': clase.profesor,
                'asignatura': asignatura,
                'asignatura_key': asignatura.lower(),
                'asignatura_color': asignatura_color,
                'curso': clase.curso.nombre if getattr(clase, 'curso_id', None) else '',
                'tiene_conversacion': tiene_conversacion,
                'conversacion_id': (
                    existente['conversacion'].id_conversacion if existente else None
                ),
                'no_leidos': existente['no_leidos'] if existente else 0,
                'ultimo_preview': preview,
            })

        profesores_contacto.sort(
            key=lambda row: (
                -row['no_leidos'],
                0 if row['tiene_conversacion'] else 1,
                row['asignatura'].lower(),
            ),
        )

        conversacion_sugerida = None
        for item in enriched:
            if item['no_leidos'] > 0:
                conversacion_sugerida = item
                break
        if conversacion_sugerida is None and enriched:
            conversacion_sugerida = enriched[0]

        insights: List[Dict[str, Any]] = []
        if no_leidos_total:
            insights.append({
                'tipo': 'alerta',
                'icono': '📬',
                'titulo': f'{no_leidos_total} mensaje(s) sin leer',
                'texto': 'Revisa tus conversaciones con profesores.',
                'url_name': 'mensajeria:bandeja_mensajes',
                'url_query': 'estado=sin_leer',
            })
        if clases_sin_conversar:
            insights.append({
                'tipo': 'sugerencia',
                'icono': '✉️',
                'titulo': f'{clases_sin_conversar} materia(s) sin chat',
                'texto': 'Puedes escribirle al profesor desde el panel lateral.',
                'url_name': None,
                'url_query': '',
            })
        notif_total = int(notificaciones_count or 0)
        if notif_total > no_leidos_total:
            insights.append({
                'tipo': 'info',
                'icono': '🔔',
                'titulo': f'{notif_total} avisos en la campana',
                'texto': (
                    'Incluye comunicados, tareas y más. '
                    'Esta pantalla solo muestra chats directos.'
                ),
                'url_name': 'dashboard',
                'url_query': 'pagina=notificaciones',
            })

        return {
            'profesores_contacto': profesores_contacto,
            'clases_sin_conversar': clases_sin_conversar,
            'conversacion_sugerida': conversacion_sugerida,
            'mensajes_insights': insights,
            'total_profesores_disponibles': len(profesores_contacto),
        }

    @staticmethod
    def get_alumno_bandeja_context(
        user,
        query_params: Optional[Dict[str, Any]] = None,
        conversacion_activa_id: Optional[int] = None,
        clases: Optional[List[Any]] = None,
        notificaciones_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Contexto de bandeja para estudiante: métricas, filtros y conversaciones enriquecidas."""
        query_params = query_params or {}
        estado_filtro = (query_params.get('estado') or '').strip()
        busqueda = (query_params.get('q') or '').strip().lower()

        conversaciones = MensajeriaService.get_conversaciones_data(user)
        conversacion_ids = [item['conversacion'].id_conversacion for item in conversaciones]

        total_mensajes = 0
        if conversacion_ids:
            total_mensajes = Mensaje.objects.filter(
                conversacion_id__in=conversacion_ids,
            ).count()

        enriched = []
        for item in conversaciones:
            conv = item['conversacion']
            clase = conv.clase
            destinatario = item['destinatario']
            ultimo = item['ultimo_mensaje']
            asignatura = clase.asignatura.nombre if clase.asignatura_id else 'Clase'
            asignatura_color = ''
            if clase.asignatura_id and getattr(clase.asignatura, 'color', None):
                asignatura_color = clase.asignatura.color
            curso = clase.curso.nombre if clase.curso_id else ''
            con_profesor = bool(clase.profesor_id and destinatario.id == clase.profesor_id)

            enriched.append({
                **item,
                'asignatura': asignatura,
                'asignatura_key': asignatura.lower(),
                'asignatura_color': asignatura_color,
                'curso': curso,
                'con_profesor': con_profesor,
                'activa': conversacion_activa_id == conv.id_conversacion,
                'iniciales': (
                    (destinatario.nombre[:1] if destinatario.nombre else '')
                    + (destinatario.apellido_paterno[:1] if destinatario.apellido_paterno else '')
                ).upper() or '?',
            })

        no_leidos_total = sum(item['no_leidos'] for item in enriched)
        conversaciones_count = len(enriched)
        con_profesores = sum(1 for item in enriched if item['con_profesor'])

        filtradas = enriched
        if estado_filtro == 'sin_leer':
            filtradas = [item for item in filtradas if item['no_leidos'] > 0]
        elif estado_filtro == 'profesores':
            filtradas = [item for item in filtradas if item['con_profesor']]

        if busqueda:
            filtradas = [
                item for item in filtradas
                if busqueda in item['destinatario'].get_full_name().lower()
                or busqueda in item['asignatura'].lower()
                or busqueda in item['curso'].lower()
                or (
                    item['ultimo_mensaje']
                    and busqueda in (item['ultimo_mensaje'].contenido or '').lower()
                )
            ]

        filtros_activos = bool(estado_filtro or busqueda)
        inteligencia = MensajeriaService._build_mensajeria_inteligencia(
            enriched,
            clases,
            no_leidos_total,
            notificaciones_count=notificaciones_count,
        )
        clases_sin_conversar = inteligencia['clases_sin_conversar']
        total_profesores = inteligencia['total_profesores_disponibles']

        hero_subtitle = 'Comunícate con profesores y la administración del colegio'
        if no_leidos_total:
            hero_subtitle = (
                f'Tienes {no_leidos_total} mensaje(s) sin leer en '
                f'{conversaciones_count} conversación(es)'
            )
        elif clases_sin_conversar and total_profesores:
            hero_subtitle = (
                f'Puedes escribir a {total_profesores} profesor(es); '
                f'{clases_sin_conversar} materia(s) aún sin conversación'
            )
        elif conversaciones_count:
            hero_subtitle = (
                f'{conversaciones_count} conversación(es) activa(s) · '
                f'{total_mensajes} mensaje(s) en total'
            )

        return {
            'conversaciones': filtradas,
            'conversaciones_todas': enriched,
            'mensajes_stats': {
                'no_leidos': no_leidos_total,
                'conversaciones': conversaciones_count,
                'con_profesores': con_profesores,
                'total_mensajes': total_mensajes,
            },
            'no_leidos_count': no_leidos_total,
            'conversaciones_count': conversaciones_count,
            'con_profesores_count': con_profesores,
            'total_mensajes_count': total_mensajes,
            'estado_filtro': estado_filtro,
            'busqueda': query_params.get('q', '').strip(),
            'filtros_activos': filtros_activos,
            'hero_subtitle_mensajes': hero_subtitle,
            'tiene_conversaciones': conversaciones_count > 0,
            'hay_resultados': len(filtradas) > 0,
            **inteligencia,
        }

    @staticmethod
    def _build_profesor_mensajeria_inteligencia(
        user,
        enriched: List[Dict[str, Any]],
        clases: Optional[List[Any]],
        no_leidos_total: int,
        notificaciones_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Contactos estudiantes por clase e insights para bandeja docente."""
        from backend.apps.cursos.models import ClaseEstudiante

        conv_por_estudiante: Dict[tuple, Dict[str, Any]] = {}
        for item in enriched:
            clase = item['conversacion'].clase
            if clase.profesor_id != user.id:
                continue
            otro = item['destinatario']
            if otro.id == user.id:
                continue
            conv_por_estudiante[(clase.id, otro.id)] = item

        estudiantes_contacto: List[Dict[str, Any]] = []
        estudiantes_sin_chat = 0
        clases_sin_conversar = 0

        for clase in clases or []:
            if clase.profesor_id != user.id:
                continue
            tiene_alguna_conv = False
            inscripciones = (
                ClaseEstudiante._base_manager.filter(clase=clase, activo=True)
                .select_related('estudiante')
                .order_by(
                    'estudiante__apellido_paterno',
                    'estudiante__apellido_materno',
                    'estudiante__nombre',
                )
            )
            for rel in inscripciones:
                estudiante = rel.estudiante
                if not estudiante.is_active:
                    continue
                existente = conv_por_estudiante.get((clase.id, estudiante.id))
                tiene_conversacion = bool(existente)
                if tiene_conversacion:
                    tiene_alguna_conv = True
                else:
                    estudiantes_sin_chat += 1
                ultimo = existente['ultimo_mensaje'] if existente else None
                preview = ''
                if ultimo and getattr(ultimo, 'contenido', None):
                    preview = (ultimo.contenido or '')[:100]
                asignatura = (
                    clase.asignatura.nombre if getattr(clase, 'asignatura_id', None) else 'Clase'
                )
                asignatura_color = ''
                if getattr(clase, 'asignatura_id', None) and getattr(
                    clase.asignatura, 'color', None
                ):
                    asignatura_color = clase.asignatura.color
                estudiantes_contacto.append({
                    'clase': clase,
                    'estudiante': estudiante,
                    'asignatura': asignatura,
                    'asignatura_key': asignatura.lower(),
                    'asignatura_color': asignatura_color,
                    'curso': clase.curso.nombre if getattr(clase, 'curso_id', None) else '',
                    'tiene_conversacion': tiene_conversacion,
                    'conversacion_id': (
                        existente['conversacion'].id_conversacion if existente else None
                    ),
                    'no_leidos': existente['no_leidos'] if existente else 0,
                    'ultimo_preview': preview,
                    'iniciales': (
                        (estudiante.nombre[:1] if estudiante.nombre else '')
                        + (
                            estudiante.apellido_paterno[:1]
                            if estudiante.apellido_paterno
                            else ''
                        )
                    ).upper()
                    or '?',
                })
            if not tiene_alguna_conv and inscripciones.exists():
                clases_sin_conversar += 1

        estudiantes_contacto.sort(
            key=lambda row: (
                -row['no_leidos'],
                0 if row['tiene_conversacion'] else 1,
                row['asignatura'].lower(),
                row['estudiante'].get_full_name().lower(),
            ),
        )

        conversacion_sugerida = None
        for item in enriched:
            if item['no_leidos'] > 0:
                conversacion_sugerida = item
                break
        if conversacion_sugerida is None and enriched:
            conversacion_sugerida = enriched[0]

        insights: List[Dict[str, Any]] = []
        if no_leidos_total:
            insights.append({
                'tipo': 'alerta',
                'icono': '📬',
                'titulo': f'{no_leidos_total} mensaje(s) sin leer',
                'texto': 'Responde a familias y estudiantes desde tus conversaciones.',
                'url_name': 'mensajeria:bandeja_mensajes',
                'url_query': 'estado=sin_leer',
            })
        if estudiantes_sin_chat:
            insights.append({
                'tipo': 'sugerencia',
                'icono': '✉️',
                'titulo': f'{estudiantes_sin_chat} contacto(s) sin chat',
                'texto': 'Inicia conversación desde el panel lateral o el detalle de cada clase.',
                'url_name': 'dashboard',
                'url_query': 'pagina=mis_clases',
            })
        if clases_sin_conversar:
            insights.append({
                'tipo': 'info',
                'icono': '📚',
                'titulo': f'{clases_sin_conversar} clase(s) sin mensajes',
                'texto': 'Aún no hay conversaciones en esas asignaturas.',
                'url_name': None,
                'url_query': '',
            })
        notif_total = int(notificaciones_count or 0)
        if notif_total > no_leidos_total:
            insights.append({
                'tipo': 'info',
                'icono': '🔔',
                'titulo': f'{notif_total} avisos en la campana',
                'texto': 'Comunicados, tareas y alertas del portal (fuera del chat directo).',
                'url_name': 'dashboard',
                'url_query': 'pagina=notificaciones',
            })
        if not insights:
            insights.append({
                'tipo': 'info',
                'icono': '💬',
                'titulo': 'Bandeja al día',
                'texto': 'No hay mensajes pendientes ni alertas de mensajería.',
                'url_name': None,
                'url_query': '',
            })

        contactos_prioridad: List[Dict[str, Any]] = []
        vistos = set()
        for row in estudiantes_contacto:
            if row['no_leidos'] and row.get('conversacion_id'):
                key = ('c', row['conversacion_id'])
                if key not in vistos:
                    contactos_prioridad.append({**row, 'motivo': 'no_leidos'})
                    vistos.add(key)
            if len(contactos_prioridad) >= 4:
                break
        if len(contactos_prioridad) < 4:
            for row in estudiantes_contacto:
                if row['tiene_conversacion']:
                    continue
                key = ('s', row['estudiante'].id, row['clase'].id)
                if key in vistos:
                    continue
                contactos_prioridad.append({**row, 'motivo': 'sin_chat'})
                vistos.add(key)
                if len(contactos_prioridad) >= 4:
                    break

        return {
            'estudiantes_contacto': estudiantes_contacto,
            'profesores_contacto': [],
            'estudiantes_sin_chat': estudiantes_sin_chat,
            'clases_sin_conversar': clases_sin_conversar,
            'conversacion_sugerida': conversacion_sugerida,
            'mensajes_insights': insights,
            'mm_contactos_prioridad': contactos_prioridad,
            'total_estudiantes_contactables': len(estudiantes_contacto),
            'mis_clases_count': len(clases or []),
        }

    @staticmethod
    def get_profesor_bandeja_context(
        user,
        query_params: Optional[Dict[str, Any]] = None,
        conversacion_activa_id: Optional[int] = None,
        clases: Optional[List[Any]] = None,
        notificaciones_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Bandeja de mensajes para docente (estudiantes/familias por clase)."""
        query_params = query_params or {}
        estado_filtro = (query_params.get('estado') or '').strip()
        busqueda = (query_params.get('q') or '').strip().lower()

        conversaciones = MensajeriaService.get_conversaciones_data(user)
        conversacion_ids = [item['conversacion'].id_conversacion for item in conversaciones]
        total_mensajes = 0
        if conversacion_ids:
            total_mensajes = Mensaje.objects.filter(
                conversacion_id__in=conversacion_ids,
            ).count()

        enriched = []
        for item in conversaciones:
            conv = item['conversacion']
            clase = conv.clase
            if clase.profesor_id != user.id:
                continue
            destinatario = item['destinatario']
            ultimo = item['ultimo_mensaje']
            asignatura = clase.asignatura.nombre if clase.asignatura_id else 'Clase'
            asignatura_color = ''
            if clase.asignatura_id and getattr(clase.asignatura, 'color', None):
                asignatura_color = clase.asignatura.color
            curso = clase.curso.nombre if clase.curso_id else ''
            con_estudiante = destinatario.id != user.id

            enriched.append({
                **item,
                'asignatura': asignatura,
                'asignatura_key': asignatura.lower(),
                'asignatura_color': asignatura_color,
                'curso': curso,
                'con_profesor': False,
                'con_estudiante': con_estudiante,
                'activa': conversacion_activa_id == conv.id_conversacion,
                'iniciales': (
                    (destinatario.nombre[:1] if destinatario.nombre else '')
                    + (
                        destinatario.apellido_paterno[:1]
                        if destinatario.apellido_paterno
                        else ''
                    )
                ).upper()
                or '?',
            })

        no_leidos_total = sum(item['no_leidos'] for item in enriched)
        conversaciones_count = len(enriched)
        con_estudiantes = sum(1 for item in enriched if item.get('con_estudiante'))

        filtradas = enriched
        if estado_filtro == 'sin_leer':
            filtradas = [item for item in filtradas if item['no_leidos'] > 0]
        elif estado_filtro == 'estudiantes':
            filtradas = [item for item in filtradas if item.get('con_estudiante')]

        if busqueda:
            filtradas = [
                item for item in filtradas
                if busqueda in item['destinatario'].get_full_name().lower()
                or busqueda in item['asignatura'].lower()
                or busqueda in item['curso'].lower()
                or (
                    item['ultimo_mensaje']
                    and busqueda in (item['ultimo_mensaje'].contenido or '').lower()
                )
            ]

        inteligencia = MensajeriaService._build_profesor_mensajeria_inteligencia(
            user,
            enriched,
            clases,
            no_leidos_total,
            notificaciones_count=notificaciones_count,
        )

        clases_con_estudiantes = []
        from backend.apps.cursos.models import ClaseEstudiante

        for clase in clases or []:
            if clase.profesor_id != user.id:
                continue
            ests = [
                rel.estudiante
                for rel in ClaseEstudiante._base_manager.filter(
                    clase=clase, activo=True
                ).select_related('estudiante')
                if rel.estudiante.is_active
            ]
            clases_con_estudiantes.append({'clase': clase, 'estudiantes': ests})

        hero_subtitle = 'Comunícate con estudiantes y apoderados de tus clases.'
        if no_leidos_total:
            hero_subtitle = (
                f'Tienes {no_leidos_total} mensaje(s) sin leer en '
                f'{conversaciones_count} conversación(es).'
            )
        elif inteligencia['estudiantes_sin_chat']:
            hero_subtitle = (
                f'{inteligencia["estudiantes_sin_chat"]} contacto(s) aún sin conversación · '
                f'{len(clases or [])} clase(s) activas'
            )
        elif conversaciones_count:
            hero_subtitle = (
                f'{conversaciones_count} conversación(es) · '
                f'{total_mensajes} mensaje(s) en total'
            )

        return {
            'conversaciones': filtradas,
            'conversaciones_todas': enriched,
            'no_leidos_count': no_leidos_total,
            'conversaciones_count': conversaciones_count,
            'con_profesores_count': con_estudiantes,
            'con_estudiantes_count': con_estudiantes,
            'total_mensajes_count': total_mensajes,
            'estado_filtro': estado_filtro,
            'busqueda': query_params.get('q', '').strip(),
            'filtros_activos': bool(estado_filtro or busqueda),
            'hero_subtitle_mensajes': hero_subtitle,
            'tiene_conversaciones': conversaciones_count > 0,
            'hay_resultados': len(filtradas) > 0,
            'clases_con_estudiantes': clases_con_estudiantes,
            **inteligencia,
        }

    @staticmethod
    def validate_conversation_access(user, conversacion) -> bool:
        """
        Valida que un usuario tenga acceso a una conversación

        Args:
            user: Usuario de Django
            conversacion: Instancia del modelo Conversacion

        Returns:
            bool: True si tiene acceso
        """
        return user in (conversacion.participante1, conversacion.participante2)

    @staticmethod
    def mark_mensaje_notifications_read(user, conversacion_id: int) -> None:
        """Marca notificaciones de esta conversación al abrir el chat."""
        from backend.apps.notificaciones.models import Notificacion

        Notificacion.objects.filter(
            destinatario=user,
            tipo='mensaje_nuevo',
            leido=False,
            enlace__icontains=f'/mensajeria/conversacion/{conversacion_id}',
        ).update(leido=True, fecha_lectura=timezone.now())

    @staticmethod
    def mark_conversation_as_read(user, conversacion) -> None:
        """
        Marca todos los mensajes de una conversación como leídos para un usuario

        Args:
            user: Usuario que marca como leído
            conversacion: Instancia del modelo Conversacion
        """
        conversacion.marcar_leidos(user)

    @staticmethod
    def send_message(conversacion, emisor, receptor, contenido=None, archivo=None) -> Any:
        """
        Envía un mensaje en una conversación

        Args:
            conversacion: Instancia del modelo Conversacion
            emisor: Usuario emisor
            receptor: Usuario receptor
            contenido: Contenido del mensaje (opcional)
            archivo: Archivo adjunto (opcional)

        Returns:
            Mensaje: El mensaje creado
        
        Raises:
            PrerequisiteException: Si emisor o receptor están inactivos
        """
        from ..models import Mensaje

        IntegrityService.validate_school_integrity_or_raise(
            school_id=conversacion.clase.colegio.rbd,
            action='SEND_MESSAGE',
        )
        
        # VALIDACIÓN DEFENSIVA: Verificar que emisor esté activo
        if not emisor.is_active:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                user_message='No puedes enviar mensajes: tu cuenta está inactiva',
                context={'emisor_id': emisor.id}
            )
        
        # VALIDACIÓN DEFENSIVA: Verificar que receptor esté activo
        if not receptor.is_active:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                user_message=f'No se puede enviar mensaje: el usuario {receptor.email} está inactivo',
                context={'receptor_id': receptor.id}
            )

        # VALIDACIÓN DEFENSIVA: Conversación activa y participantes válidos
        if not conversacion.clase.activo:
            raise PrerequisiteException(
                error_type='INVALID_STATE',
                user_message='No se pueden enviar mensajes en clases inactivas',
                context={'clase_id': conversacion.clase.id_clase}
            )

        participantes = {conversacion.participante1_id, conversacion.participante2_id}
        if emisor.id not in participantes or receptor.id not in participantes:
            raise PrerequisiteException(
                error_type='INVALID_RELATIONSHIP',
                user_message='Emisor o receptor no pertenecen a la conversación',
                context={
                    'conversacion_id': conversacion.id,
                    'emisor_id': emisor.id,
                    'receptor_id': receptor.id,
                }
            )

        mensaje = Mensaje.objects.create(
            conversacion=conversacion,
            emisor=emisor,
            receptor=receptor,
            contenido=contenido,
            archivo_adjunto=archivo,
        )

        # Actualizar última actividad de la conversación
        conversacion.ultima_actividad = timezone.now()
        conversacion.save(update_fields=['ultima_actividad'])

        return mensaje

    @staticmethod
    def validate_message_data(contenido, archivo) -> Tuple[bool, str]:
        """
        Valida los datos de un mensaje

        Args:
            contenido: Contenido del mensaje
            archivo: Archivo adjunto

        Returns:
            Tuple: (es_valido, mensaje_error)
        """
        contenido = (contenido or '').strip()

        if not contenido and not archivo:
            return False, 'Escribe un mensaje o adjunta un archivo'

        return True, ''

    @staticmethod
    def validate_destinatario_for_class(clase, destinatario) -> Tuple[bool, str]:
        """
        Valida que un destinatario sea válido para una clase

        Args:
            clase: Instancia del modelo Clase
            destinatario: Usuario destinatario

        Returns:
            Tuple: (es_valido, mensaje_error)
        """
        from backend.apps.accounts.models import PerfilEstudiante

        # Si es el profesor de la clase
        if destinatario.id == clase.profesor_id:
            return True, ''

        from backend.apps.cursos.models import ClaseEstudiante

        if ClaseEstudiante.objects.filter(
            clase=clase,
            estudiante=destinatario,
            activo=True,
        ).exists():
            return True, ''

        if hasattr(destinatario, 'perfil_apoderado'):
            if ClaseEstudiante.objects.filter(
                clase=clase,
                activo=True,
                estudiante__apoderados__user=destinatario,
            ).exists():
                return True, ''

        perfil_dest = PerfilEstudiante.objects.filter(user=destinatario).first()
        if perfil_dest and perfil_dest.ciclo_actual == clase.curso.ciclo_academico:
            return True, ''

        return False, 'El destinatario no pertenece a esta clase'

    @staticmethod
    def get_conversation_messages(conversacion) -> List[Any]:
        """
        Obtiene los mensajes de una conversación ordenados por fecha

        Args:
            conversacion: Instancia del modelo Conversacion

        Returns:
            List: Lista de mensajes
        """
        return list(
            Mensaje.objects.filter(conversacion=conversacion).select_related('emisor', 'receptor').order_by('fecha_envio')
        )

    @staticmethod
    def get_conversacion_for_user(user, id_conversacion: int):
        """
        Obtiene conversación con validación de acceso.
        """
        from django.shortcuts import get_object_or_404
        from ..models import Conversacion

        conversacion = get_object_or_404(
            Conversacion.objects.select_related('clase', 'clase__asignatura', 'clase__curso', 'participante1', 'participante2'),
            id_conversacion=id_conversacion,
        )

        if not MensajeriaService.validate_conversation_access(user, conversacion):
            return None

        return conversacion
