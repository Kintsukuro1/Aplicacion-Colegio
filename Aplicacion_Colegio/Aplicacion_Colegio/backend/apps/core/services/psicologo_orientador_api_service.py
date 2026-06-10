"""
Service para operaciones del Psicólogo Orientador vía API.
Centraliza el acceso ORM para entrevistas, derivaciones y PIE.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PsicologoOrientadorApiService:
    """Encapsula el acceso ORM del psicólogo orientador."""

    # ------------------------------------------------------------------
    # Estudiantes
    # ------------------------------------------------------------------

    @staticmethod
    def list_estudiantes(rbd: int) -> list[dict]:
        """Lista estudiantes activos del colegio."""
        from backend.apps.accounts.models import User

        qs = User.objects.filter(
            rbd_colegio=rbd,
            role__nombre__in=['Alumno', 'Estudiante'],
            is_active=True,
        ).values('id', 'nombre', 'apellido_paterno', 'apellido_materno').order_by('apellido_paterno', 'nombre')

        return [
            {
                'id': e['id'],
                'nombre': (
                    f"{e['nombre']} {e['apellido_paterno']} {e.get('apellido_materno') or ''}"
                ).strip(),
            }
            for e in qs
        ]

    @staticmethod
    def get_estudiante_or_none(estudiante_id, rbd: int, require_student_role: bool = False):
        """Retorna User del colegio o None. Si require_student_role filtra por nombres de roles de alumno."""
        from backend.apps.accounts.models import User

        filters: dict = {'id': estudiante_id, 'rbd_colegio': rbd}
        if require_student_role:
            filters['role__nombre__in'] = ['Alumno', 'Estudiante']

        try:
            return User.objects.get(**filters)
        except User.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Entrevistas de orientación
    # ------------------------------------------------------------------

    @staticmethod
    def crear_entrevista(*, estudiante, rbd: int, psicologo, fecha: str, motivo: str,
                         observaciones: str, acuerdos: str, seguimiento: bool,
                         fecha_siguiente=None):
        """Crea y retorna una EntrevistaOrientacion."""
        from backend.apps.core.models import EntrevistaOrientacion

        return EntrevistaOrientacion.objects.create(
            estudiante=estudiante,
            colegio_id=rbd,
            psicologo=psicologo,
            fecha=fecha,
            motivo=motivo,
            observaciones=observaciones,
            acuerdos=acuerdos,
            seguimiento_requerido=seguimiento,
            fecha_siguiente_sesion=fecha_siguiente,
            confidencial=True,
        )

    # ------------------------------------------------------------------
    # Derivaciones externas
    # ------------------------------------------------------------------

    @staticmethod
    def crear_derivacion(*, estudiante, rbd: int, derivado_por, profesional: str,
                         especialidad: str, motivo: str, fecha_derivacion: str):
        """Crea y retorna una DerivacionExterna."""
        from backend.apps.core.models import DerivacionExterna

        return DerivacionExterna.objects.create(
            estudiante=estudiante,
            colegio_id=rbd,
            derivado_por=derivado_por,
            profesional_destino=profesional,
            especialidad=especialidad,
            motivo=motivo,
            fecha_derivacion=fecha_derivacion,
            estado='PENDIENTE',
        )

    @staticmethod
    def get_derivacion_or_none(derivacion_id, rbd: int):
        """Retorna DerivacionExterna o None."""
        from backend.apps.core.models import DerivacionExterna

        try:
            return DerivacionExterna.objects.get(id_derivacion=derivacion_id, colegio_id=rbd)
        except DerivacionExterna.DoesNotExist:
            return None

    @staticmethod
    def actualizar_derivacion(derivacion, *, nuevo_estado: str, informe: str = '',
                               fecha_retorno=None) -> None:
        """Actualiza estado y campos opcionales de una derivación."""
        derivacion.estado = nuevo_estado
        if informe:
            derivacion.informe_retorno = informe
        if nuevo_estado == 'COMPLETADA' and fecha_retorno:
            derivacion.fecha_retorno = fecha_retorno
        derivacion.save()

    # ------------------------------------------------------------------
    # PIE
    # ------------------------------------------------------------------

    @staticmethod
    def toggle_pie_status(estudiante, *, requiere_pie: bool):
        """Activa o desactiva el estado PIE del estudiante."""
        from backend.apps.accounts.models import PerfilEstudiante

        perfil, _ = PerfilEstudiante.objects.get_or_create(user=estudiante)
        perfil.requiere_pie = requiere_pie
        perfil.save()
        return perfil

    # ------------------------------------------------------------------
    # Citaciones a Apoderados
    # ------------------------------------------------------------------

    @staticmethod
    def crear_citacion(*, estudiante, rbd: int, solicitado_por, fecha_citacion: str, motivo: str):
        """Crea y retorna una CitacionApoderado."""
        from backend.apps.core.models import CitacionApoderado

        return CitacionApoderado.objects.create(
            estudiante=estudiante,
            colegio_id=rbd,
            solicitado_por=solicitado_por,
            fecha_citacion=fecha_citacion,
            motivo=motivo,
            estado='PENDIENTE',
        )

    @staticmethod
    def get_citacion_or_none(citacion_id, rbd: int):
        """Retorna CitacionApoderado o None."""
        from backend.apps.core.models import CitacionApoderado

        try:
            return CitacionApoderado.objects.get(id_citacion=citacion_id, colegio_id=rbd)
        except CitacionApoderado.DoesNotExist:
            return None

    @staticmethod
    def actualizar_citacion(citacion, *, nuevo_estado: str, observaciones: str = '',
                            acuerdos: str = '') -> None:
        """Actualiza el estado y las actas de una citación de apoderado."""
        citacion.estado = nuevo_estado
        if observaciones:
            citacion.observaciones = observaciones
        if acuerdos:
            citacion.acuerdos = acuerdos
        citacion.save()

    # ------------------------------------------------------------------
    # Casos de Bullying y Convivencia Escolar
    # ------------------------------------------------------------------

    @staticmethod
    def crear_caso_bullying(*, estudiante_implicado, rbd: int, registrado_por,
                             tipo_falta: str, descripcion_hechos: str, apoderado_notificado: bool):
        """Crea y retorna un CasoBullyingConvivencia."""
        from backend.apps.core.models import CasoBullyingConvivencia

        return CasoBullyingConvivencia.objects.create(
            estudiante_implicado=estudiante_implicated if False else estudiante_implicado, # safety check
            colegio_id=rbd,
            registrado_por=registrado_por,
            tipo_falta=tipo_falta,
            descripcion_hechos=descripcion_hechos,
            apoderado_notificado=apoderado_notificado,
            estado='ABIERTO',
        )

    @staticmethod
    def get_caso_bullying_or_none(caso_id, rbd: int):
        """Retorna CasoBullyingConvivencia o None."""
        from backend.apps.core.models import CasoBullyingConvivencia

        try:
            return CasoBullyingConvivencia.objects.get(id_caso=caso_id, colegio_id=rbd)
        except CasoBullyingConvivencia.DoesNotExist:
            return None

    @staticmethod
    def actualizar_caso_bullying(caso, *, nuevo_estado: str, medidas_tomadas: str = '',
                                 apoderado_notificado: bool = False) -> None:
        """Actualiza el estado y medidas aplicadas del caso de Convivencia."""
        caso.estado = nuevo_estado
        if medidas_tomadas:
            caso.medidas_tomadas = medidas_tomadas
        if apoderado_notificado:
            caso.apoderado_notificado = apoderado_notificado
        caso.save()

