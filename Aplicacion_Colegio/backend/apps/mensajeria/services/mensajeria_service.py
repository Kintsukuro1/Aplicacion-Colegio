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

        # Si es estudiante activo del curso
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
    def get_alumno_bandeja_context(
        user,
        query_params: Optional[Dict[str, Any]] = None,
        conversacion_activa_id: Optional[int] = None,
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
        hero_subtitle = 'Comunícate con profesores y la administración del colegio'
        if no_leidos_total:
            hero_subtitle = (
                f'Tienes {no_leidos_total} mensaje(s) sin leer en '
                f'{conversaciones_count} conversación(es)'
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

        # Si es estudiante del mismo curso
        perfil_dest = PerfilEstudiante.objects.filter(user=destinatario).first()
        if not perfil_dest or perfil_dest.ciclo_actual != clase.curso.ciclo_academico:
            return False, 'Destinatario inválido para esta clase'

        return True, ''

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
