from __future__ import annotations

from backend.apps.accounts.models import User
from backend.apps.core.services.escuela_management_service import EscuelaManagementService
from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.institucion.models import Colegio


class ColegioService:
    @classmethod
    def validations(cls, *, data: dict, rbd: int | None = None):
        required_fields = [
            'rut_establecimiento',
            'nombre',
            'comuna_id',
            'tipo_establecimiento_id',
            'dependencia_id',
        ]
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f'Campo requerido: {field}')

        correo = data.get('correo')
        if correo:
            query = Colegio.objects.filter(correo=correo)
            if rbd is not None:
                query = query.exclude(rbd=rbd)
            if query.exists():
                raise ValueError('El correo del colegio ya está en uso por otro establecimiento.')

    @classmethod
    def create(cls, *, user, data: dict):
        cls.validations(data=data)
        return EscuelaManagementService.crear_colegio(user, data)

    @classmethod
    def update(cls, *, user, rbd: int, data: dict):
        cls.validations(data=data, rbd=rbd)
        IntegrityService.validate_colegio_update(rbd)
        colegio = Colegio.objects.get(rbd=rbd)

        nuevo_correo = data.get('correo')
        if nuevo_correo:
            correo_en_uso = Colegio.objects.filter(correo=nuevo_correo).exclude(rbd=rbd).exists()
            if correo_en_uso:
                raise ValueError('El correo del colegio ya está en uso por otro establecimiento.')

        colegio.rut_establecimiento = data['rut_establecimiento']
        colegio.nombre = data['nombre']
        colegio.direccion = data.get('direccion')
        colegio.telefono = data.get('telefono')
        colegio.correo = nuevo_correo
        colegio.web = data.get('web')
        colegio.capacidad_maxima = data.get('capacidad_maxima') or None
        colegio.fecha_fundacion = data.get('fecha_fundacion') or None
        colegio.comuna_id = data['comuna_id']
        colegio.tipo_establecimiento_id = data['tipo_establecimiento_id']
        colegio.dependencia_id = data['dependencia_id']
        colegio.save()

        return colegio

    @classmethod
    def get(cls, *, rbd: int):
        return Colegio.objects.get(rbd=rbd)

    @classmethod
    def update_basic_info(cls, *, user, rbd: int, data: dict):
        IntegrityService.validate_colegio_update(rbd)

        colegio = Colegio.objects.get(rbd=rbd)
        colegio.nombre = data['nombre']
        colegio.direccion = data.get('direccion')
        colegio.telefono = data.get('telefono')
        colegio.correo = data.get('correo')
        colegio.web = data.get('web')
        colegio.capacidad_maxima = data.get('capacidad_maxima')
        colegio.fecha_fundacion = data.get('fecha_fundacion')
        colegio.save()
        return colegio

    @classmethod
    def delete(cls, *, user, rbd: int):
        IntegrityService.validate_colegio_deletion(rbd)
        if User.objects.filter(rbd_colegio=rbd, is_active=True).exists():
            raise ValueError('No se puede eliminar la escuela porque tiene usuarios activos asociados.')

        return EscuelaManagementService.eliminar_colegio(user, str(rbd))
