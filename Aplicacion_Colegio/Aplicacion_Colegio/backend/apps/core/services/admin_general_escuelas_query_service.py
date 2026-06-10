from __future__ import annotations

from backend.apps.accounts.models import User
from backend.apps.institucion.models import Colegio, Comuna, DependenciaAdministrativa, Region, TipoEstablecimiento


class AdminGeneralEscuelasQueryService:
    @staticmethod
    def list_escuelas(*, region_id=None, tipo_id=None, dependencia_id=None, search=None):
        escuelas = Colegio.objects.select_related(
            'comuna__region', 'tipo_establecimiento', 'dependencia'
        ).order_by('nombre')

        if region_id:
            escuelas = escuelas.filter(comuna__region_id=region_id)
        if tipo_id:
            escuelas = escuelas.filter(tipo_establecimiento_id=tipo_id)
        if dependencia_id:
            escuelas = escuelas.filter(dependencia_id=dependencia_id)
        if search:
            escuelas = escuelas.filter(nombre__icontains=search) | escuelas.filter(rbd__icontains=search)

        return escuelas

    @staticmethod
    def list_filter_data(*, include_comunas=False):
        regiones = Region.objects.prefetch_related('comunas').all() if include_comunas else Region.objects.all()
        tipos_establecimiento = TipoEstablecimiento.objects.all()
        dependencias = DependenciaAdministrativa.objects.all()
        return regiones, tipos_establecimiento, dependencias

    @staticmethod
    def get_escuela_by_rbd(rbd):
        return Colegio.objects.get(rbd=rbd)

    @staticmethod
    def get_escuela_detail_by_rbd(rbd):
        return Colegio.objects.select_related(
            'comuna__region', 'tipo_establecimiento', 'dependencia'
        ).get(rbd=rbd)

    @staticmethod
    def get_escuela_detail_or_none(rbd):
        return Colegio.objects.select_related(
            'comuna__region', 'tipo_establecimiento', 'dependencia'
        ).filter(rbd=rbd).first()

    @staticmethod
    def get_user_counts_by_school(rbd):
        total_usuarios = User.objects.filter(rbd_colegio=rbd).count()
        total_profesores = User.objects.filter(rbd_colegio=rbd, perfil_profesor__isnull=False).count()
        total_estudiantes = User.objects.filter(rbd_colegio=rbd, perfil_estudiante__isnull=False).count()
        return total_usuarios, total_profesores, total_estudiantes

    @staticmethod
    def has_users_for_school(rbd):
        return User.objects.filter(rbd_colegio=rbd).exists()

    @staticmethod
    def list_comunas_by_region(region_id):
        return Comuna.objects.filter(region_id=region_id).order_by('nombre')
