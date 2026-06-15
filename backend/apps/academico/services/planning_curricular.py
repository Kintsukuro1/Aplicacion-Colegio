"""Servicio de dominio para planificación curricular y banco de recursos."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from backend.apps.academico.models import (
    Planificacion, ObjetivoAprendizaje, Rubrica,
    CriterioRubrica, NivelRubrica, Evaluacion
)
from backend.apps.cursos.models import Clase, Asignatura
from backend.apps.accounts.models import User


class PlanningCurricularService:
    """
    Orquesta la lógica de negocio para la planificación curricular,
    estados de aprobación, y banco compartido (Rúbricas y Evaluaciones)
    bajo estrictas reglas multi-tenant.
    """

    @staticmethod
    def get_planificacion(
        *,
        colegio_id: int,
        planificacion_id: int,
        profesor_id: Optional[int] = None
    ) -> Planificacion:
        """Obtiene una planificación asegurando control multi-tenant y de autor."""
        filters = {
            'id_planificacion': planificacion_id,
            'colegio_id': colegio_id,
            'activa': True
        }
        if profesor_id is not None:
            filters['clase__profesor_id'] = profesor_id

        try:
            return Planificacion.objects.select_related(
                'clase', 'clase__curso', 'clase__asignatura', 'rubrica'
            ).prefetch_related('objetivos_aprendizaje', 'objetivos', 'actividades', 'recursos', 'evaluaciones').get(**filters)
        except Planificacion.DoesNotExist:
            raise ValidationError("La planificación solicitada no existe o no tiene permisos para acceder a ella.")

    @staticmethod
    def list_planificaciones(
        *,
        colegio_id: int,
        profesor_id: Optional[int] = None,
        clase_id: Optional[int] = None,
        estado: Optional[str] = None
    ) -> List[Planificacion]:
        """Lista planificaciones con filtros multi-tenant aplicados."""
        qs = Planificacion.objects.filter(colegio_id=colegio_id, activa=True)

        if profesor_id is not None:
            qs = qs.filter(clase__profesor_id=profesor_id)
        if clase_id is not None:
            qs = qs.filter(clase_id=clase_id)
        if estado is not None:
            qs = qs.filter(estado=estado)

        return qs.select_related('clase', 'clase__curso', 'clase__asignatura', 'rubrica').order_by('-fecha_creacion')

    @staticmethod
    def create_planificacion(
        *,
        user,
        colegio_id: int,
        clase_id: int,
        titulo: str,
        objetivo_general: str,
        fecha_inicio: date,
        fecha_fin: date,
        objetivo_ids: Optional[List[int]] = None,
        rubrica_id: Optional[int] = None,
        ciclo_academico_id: Optional[int] = None
    ) -> Planificacion:
        """Crea una planificación en estado BORRADOR con validaciones estrictas."""
        # 1. Validar la Clase y que pertenezca al profesor y colegio
        try:
            clase = Clase.objects.get(
                id=clase_id,
                colegio_id=colegio_id,
                profesor_id=user.id,
                activo=True
            )
        except Clase.DoesNotExist:
            raise ValidationError("La clase seleccionada no existe, no está activa, o no le pertenece.")

        # 2. Validar rúbrica si es provista
        rubrica = None
        if rubrica_id:
            try:
                rubrica = Rubrica.objects.get(
                    id_rubrica=rubrica_id,
                    colegio_id=colegio_id,
                    asignatura_id=clase.asignatura_id,
                    activo=True
                )
            except Rubrica.DoesNotExist:
                raise ValidationError("La rúbrica seleccionada no es válida para este colegio o asignatura.")

        # 3. Validar los Objetivos de Aprendizaje
        oas = []
        if objetivo_ids:
            oas = ObjetivoAprendizaje.objects.filter(
                id_oa__in=objetivo_ids,
                colegio_id=colegio_id,
                asignatura_id=clase.asignatura_id,
                activo=True
            )
            if len(oas) != len(objetivo_ids):
                raise ValidationError("Uno o más Objetivos de Aprendizaje seleccionados no son válidos para esta asignatura.")

        # 4. Crear la planificación
        with transaction.atomic():
            planificacion = Planificacion.objects.create(
                colegio_id=colegio_id,
                clase=clase,
                titulo=titulo,
                objetivo_general=objetivo_general,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                rubrica=rubrica,
                ciclo_academico_id=ciclo_academico_id,
                estado='BORRADOR',
                activa=True
            )
            if oas:
                planificacion.objetivos_aprendizaje.set(oas)

            return planificacion

    @staticmethod
    def update_planificacion(
        *,
        user,
        colegio_id: int,
        planificacion_id: int,
        titulo: str,
        objetivo_general: str,
        fecha_inicio: date,
        fecha_fin: date,
        objetivo_ids: Optional[List[int]] = None,
        rubrica_id: Optional[int] = None,
        ciclo_academico_id: Optional[int] = None
    ) -> Planificacion:
        """Modifica una planificación en borrador o rechazada. Lanza error si está aprobada o enviada."""
        with transaction.atomic():
            planificacion = PlanningCurricularService.get_planificacion(
                colegio_id=colegio_id,
                planificacion_id=planificacion_id,
                profesor_id=user.id
            )

            # Inmutabilidad si está Aprobada o Enviada
            if planificacion.estado in ('APROBADA', 'ENVIADA'):
                raise ValidationError(
                    f"No es posible modificar una planificación en estado {planificacion.get_estado_display()}."
                )

            # Validar rúbrica si es provista
            rubrica = None
            if rubrica_id:
                try:
                    rubrica = Rubrica.objects.get(
                        id_rubrica=rubrica_id,
                        colegio_id=colegio_id,
                        asignatura_id=planificacion.clase.asignatura_id,
                        activo=True
                    )
                except Rubrica.DoesNotExist:
                    raise ValidationError("La rúbrica seleccionada no es válida para esta asignatura.")

            # Validar los Objetivos de Aprendizaje
            oas = []
            if objetivo_ids:
                oas = ObjetivoAprendizaje.objects.filter(
                    id_oa__in=objetivo_ids,
                    colegio_id=colegio_id,
                    asignatura_id=planificacion.clase.asignatura_id,
                    activo=True
                )
                if len(oas) != len(objetivo_ids):
                    raise ValidationError("Uno o más Objetivos de Aprendizaje seleccionados no son válidos.")

            # Actualizar campos
            planificacion.titulo = titulo
            planificacion.objetivo_general = objetivo_general
            planificacion.fecha_inicio = fecha_inicio
            planificacion.fecha_fin = fecha_fin
            planificacion.rubrica = rubrica
            if ciclo_academico_id:
                planificacion.ciclo_academico_id = ciclo_academico_id

            # Si estaba rechazada, vuelve a borrador al ser guardada de nuevo
            if planificacion.estado == 'RECHAZADA':
                planificacion.estado = 'BORRADOR'

            planificacion.save(update_fields=[
                'titulo', 'objetivo_general', 'fecha_inicio', 'fecha_fin',
                'rubrica', 'ciclo_academico', 'estado'
            ])

            # Actualizar OAs
            planificacion.objetivos_aprendizaje.set(oas)

            return planificacion

    @staticmethod
    def delete_planificacion(*, user, colegio_id: int, planificacion_id: int) -> bool:
        """Realiza un borrado lógico de una planificación si está en estado editable."""
        planificacion = PlanningCurricularService.get_planificacion(
            colegio_id=colegio_id,
            planificacion_id=planificacion_id,
            profesor_id=user.id
        )

        if planificacion.estado in ('APROBADA', 'ENVIADA'):
            raise ValidationError("No se puede eliminar una planificación ya enviada o aprobada.")

        planificacion.activa = False
        planificacion.save(update_fields=['activa'])
        return True

    @staticmethod
    def enviar_planificacion(*, user, colegio_id: int, planificacion_id: int) -> Planificacion:
        """Envía la planificación para revisión del coordinador."""
        planificacion = PlanningCurricularService.get_planificacion(
            colegio_id=colegio_id,
            planificacion_id=planificacion_id,
            profesor_id=user.id
        )

        if planificacion.estado not in ('BORRADOR', 'RECHAZADA'):
            raise ValidationError("Solo se pueden enviar planificaciones en estado Borrador o Rechazada.")

        planificacion.estado = 'ENVIADA'
        planificacion.enviada_por = user
        planificacion.fecha_envio = timezone.now()
        planificacion.save(update_fields=['estado', 'enviada_por', 'fecha_envio'])

        return planificacion

    @staticmethod
    def revisar_planificacion(
        *,
        coordinador,
        colegio_id: int,
        planificacion_id: int,
        aprobar: bool,
        observaciones: str = ''
    ) -> Planificacion:
        """Acepta o rechaza la planificación en revisión (rol Coordinador)."""
        planificacion = PlanningCurricularService.get_planificacion(
            colegio_id=colegio_id,
            planificacion_id=planificacion_id
        )

        if planificacion.estado != 'ENVIADA':
            raise ValidationError("La planificación debe estar en estado Enviada para poder ser revisada.")

        if aprobar:
            planificacion.estado = 'APROBADA'
        else:
            planificacion.estado = 'RECHAZADA'

        planificacion.observaciones_coordinador = observaciones
        planificacion.aprobado_por = coordinador
        planificacion.fecha_aprobacion = timezone.now()
        planificacion.save(update_fields=[
            'estado', 'observaciones_coordinador', 'aprobado_por', 'fecha_aprobacion'
        ])

        return planificacion

    # --- BANCO DE RÚBRICAS ---

    @staticmethod
    def list_banco_rubricas(*, colegio_id: int, asignatura_id: int) -> List[Rubrica]:
        """Obtiene rúbricas compartidas en el mismo colegio para una asignatura."""
        return Rubrica.objects.filter(
            colegio_id=colegio_id,
            asignatura_id=asignatura_id,
            activo=True,
            es_compartida=True
        ).select_related('creado_por').order_by('-fecha_creacion')

    @staticmethod
    def clone_rubrica(
        *,
        user,
        colegio_id: int,
        rubrica_id: int,
        asignatura_id: int
    ) -> Rubrica:
        """
        Clona una rúbrica y sus criterios/niveles para el docente actual.
        La rúbrica resultante es privada por defecto.
        """
        with transaction.atomic():
            try:
                source_rubrica = Rubrica.objects.filter(
                    id_rubrica=rubrica_id,
                    colegio_id=colegio_id
                ).get()
            except Rubrica.DoesNotExist:
                raise ValidationError("La rúbrica origen no existe o no pertenece a este colegio.")

            # Crear copia de la rúbrica principal
            cloned_rubrica = Rubrica.objects.create(
                colegio_id=colegio_id,
                asignatura_id=asignatura_id,
                creado_por=user,
                nombre=f"Copia de {source_rubrica.nombre}",
                descripcion=source_rubrica.descripcion,
                es_compartida=False,
                activo=True
            )

            # Copiar criterios y niveles asociados
            for criterio in source_rubrica.criterios.all():
                cloned_criterio = CriterioRubrica.objects.create(
                    rubrica=cloned_rubrica,
                    nombre=criterio.nombre,
                    descripcion=criterio.descripcion,
                    peso=criterio.peso,
                    orden=criterio.orden
                )
                for nivel in criterio.niveles.all():
                    NivelRubrica.objects.create(
                        criterio=cloned_criterio,
                        puntaje=nivel.puntaje,
                        descripcion=nivel.descripcion,
                        orden=nivel.orden
                    )

            return cloned_rubrica

    # --- BANCO DE EVALUACIONES ---

    @staticmethod
    def list_banco_evaluaciones(*, colegio_id: int, asignatura_id: int) -> List[Evaluacion]:
        """Lista evaluaciones activas del departamento (misma asignatura y colegio) para clonar."""
        return Evaluacion.objects.filter(
            colegio_id=colegio_id,
            clase__asignatura_id=asignatura_id,
            activa=True
        ).select_related(
            'clase', 'clase__profesor', 'clase__curso'
        ).order_by('-fecha_evaluacion')

    @staticmethod
    def clone_evaluacion(
        *,
        user,
        colegio_id: int,
        evaluacion_id: int,
        target_clase_id: int,
        fecha_evaluacion: date
    ) -> Evaluacion:
        """
        Clona una evaluación en una clase de destino del docente llamante,
        reseteando registros asociados (calificaciones, entregas) a un estado limpio.
        """
        with transaction.atomic():
            try:
                source_eval = Evaluacion.objects.filter(
                    id_evaluacion=evaluacion_id,
                    colegio_id=colegio_id,
                    activa=True
                ).get()
            except Evaluacion.DoesNotExist:
                raise ValidationError("La evaluación a clonar no existe o no pertenece a este colegio.")

            try:
                target_clase = Clase.objects.get(
                    id=target_clase_id,
                    colegio_id=colegio_id,
                    profesor_id=user.id,
                    activo=True
                )
            except Clase.DoesNotExist:
                raise ValidationError("La clase de destino seleccionada no existe o no le pertenece.")

            # Crear copia de la evaluación limpia de calificaciones/entregas
            cloned_eval = Evaluacion.objects.create(
                colegio_id=colegio_id,
                clase=target_clase,
                nombre=f"Copia de {source_eval.nombre}",
                fecha_evaluacion=fecha_evaluacion,
                ponderacion=source_eval.ponderacion,
                periodo=source_eval.periodo,
                tipo_evaluacion=source_eval.tipo_evaluacion,
                es_recuperacion=False,
                evaluacion_original=None,
                activa=True
            )

            return cloned_eval
