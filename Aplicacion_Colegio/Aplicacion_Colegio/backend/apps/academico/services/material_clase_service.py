"""Servicio de dominio para materiales de clase."""

from typing import Optional

from backend.apps.core.services.integrity_service import IntegrityService
from backend.common.exceptions import PrerequisiteException


class MaterialClaseService:
    """Operaciones críticas sobre `MaterialClase`."""

    @staticmethod
    def create(
        *,
        user,
        clase_id: int,
        titulo: str,
        archivo,
        descripcion: str = '',
        tipo_archivo: str = 'documento',
        es_publico: bool = False,
    ):
        from backend.apps.cursos.models import Clase
        from backend.apps.academico.models import MaterialClase

        clase = Clase.objects.filter(
            id=clase_id,
            colegio=user.colegio,
            profesor=user,
            activo=True,
        ).first()
        if not clase:
            raise PrerequisiteException(
                error_type='FORBIDDEN',
                context={'message': 'No tienes permisos para subir material en esta clase.'}
            )

        IntegrityService.validate_school_integrity_or_raise(
            school_id=user.rbd_colegio,
            action='MATERIAL_CLASE_CREATE',
        )

        return MaterialClase.objects.create(
            colegio=user.colegio,
            clase_id=clase_id,
            titulo=titulo,
            descripcion=descripcion,
            archivo=archivo,
            tipo_archivo=tipo_archivo,
            es_publico=es_publico,
            tamanio_bytes=getattr(archivo, 'size', 0),
            subido_por=user,
        )

    @staticmethod
    def deactivate(*, user, clase_id: int, material_id: int):
        from backend.apps.academico.models import MaterialClase

        material = MaterialClase.objects.get(
            id_material=material_id,
            clase_id=clase_id,
            subido_por=user,
        )

        IntegrityService.validate_school_integrity_or_raise(
            school_id=user.rbd_colegio,
            action='MATERIAL_CLASE_DEACTIVATE',
        )

        material.activo = False
        material.save(update_fields=['activo'])
        return material

    @staticmethod
    def toggle_visibility(*, user, clase_id: int, material_id: int):
        from backend.apps.academico.models import MaterialClase

        material = MaterialClase.objects.get(
            id_material=material_id,
            clase_id=clase_id,
            subido_por=user,
        )

        IntegrityService.validate_school_integrity_or_raise(
            school_id=user.rbd_colegio,
            action='MATERIAL_CLASE_TOGGLE_VISIBILITY',
        )

        material.es_publico = not material.es_publico
        material.save(update_fields=['es_publico'])
        return material
