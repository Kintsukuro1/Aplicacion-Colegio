"""
Service para operaciones de Bibliotecario Digital vía API.
Centraliza el acceso ORM para recursos digitales y préstamos.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class BibliotecarioApiService:
    """Encapsula las operaciones ORM del bibliotecario para mantener las vistas limpias."""

    # ------------------------------------------------------------------
    # Recursos
    # ------------------------------------------------------------------

    @staticmethod
    def list_recursos(rbd: int) -> list[dict]:
        """Lista recursos publicados del colegio."""
        from backend.apps.core.models import RecursoDigital

        qs = RecursoDigital.objects.filter(
            colegio_id=rbd,
            publicado=True,
        ).values('id_recurso', 'titulo', 'tipo').order_by('titulo')

        return [
            {'id': r['id_recurso'], 'titulo': r['titulo'], 'tipo': r['tipo']}
            for r in qs
        ]

    @staticmethod
    def crear_recurso(*, rbd: int, user, titulo: str, descripcion: str, tipo: str,
                      url_externa: str, publicado: bool, es_plan_lector: bool):
        """Crea y retorna un RecursoDigital."""
        from backend.apps.core.models import RecursoDigital

        return RecursoDigital.objects.create(
            colegio_id=rbd,
            titulo=titulo,
            descripcion=descripcion,
            tipo=tipo,
            url_externa=url_externa,
            publicado=publicado,
            es_plan_lector=es_plan_lector,
            publicado_por=user,
        )

    @staticmethod
    def get_recurso_or_none(recurso_id, rbd: int):
        """Retorna RecursoDigital o None."""
        from backend.apps.core.models import RecursoDigital

        try:
            return RecursoDigital.objects.get(id_recurso=recurso_id, colegio_id=rbd)
        except RecursoDigital.DoesNotExist:
            return None

    @staticmethod
    def toggle_publicar(recurso) -> bool:
        """Cicla el estado publicado y retorna nuevo valor."""
        recurso.publicado = not recurso.publicado
        recurso.save(update_fields=['publicado'])
        return recurso.publicado

    # ------------------------------------------------------------------
    # Usuarios
    # ------------------------------------------------------------------

    @staticmethod
    def list_usuarios(rbd: int) -> list[dict]:
        """Lista usuarios activos del colegio para préstamos."""
        from backend.apps.accounts.models import User

        qs = User.objects.filter(
            rbd_colegio=rbd,
            is_active=True,
        ).values('id', 'nombre', 'apellido_paterno', 'apellido_materno').order_by('apellido_paterno', 'nombre')

        return [
            {
                'id': u['id'],
                'nombre': (
                    f"{u['nombre']} {u['apellido_paterno']} {u.get('apellido_materno') or ''}"
                ).strip(),
            }
            for u in qs
        ]

    @staticmethod
    def get_usuario_or_none(usuario_id, rbd: int):
        """Retorna User o None."""
        from backend.apps.accounts.models import User

        try:
            return User.objects.get(id=usuario_id, rbd_colegio=rbd)
        except User.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Préstamos
    # ------------------------------------------------------------------

    @staticmethod
    def crear_prestamo(*, recurso, usuario, rbd: int, fecha_devolucion: str):
        """Crea y retorna un PrestamoRecurso."""
        from backend.apps.core.models import PrestamoRecurso

        return PrestamoRecurso.objects.create(
            recurso=recurso,
            usuario=usuario,
            colegio_id=rbd,
            fecha_devolucion_esperada=fecha_devolucion,
            estado='ACTIVO',
        )

    @staticmethod
    def get_prestamo_or_none(prestamo_id, rbd: int):
        """Retorna PrestamoRecurso o None."""
        from backend.apps.core.models import PrestamoRecurso

        try:
            return PrestamoRecurso.objects.get(id_prestamo=prestamo_id, colegio_id=rbd)
        except PrestamoRecurso.DoesNotExist:
            return None

    @staticmethod
    def registrar_devolucion(prestamo) -> None:
        """Marca el préstamo como devuelto hoy."""
        prestamo.estado = 'DEVUELTO'
        prestamo.fecha_devolucion_real = date.today()
        prestamo.save(update_fields=['estado', 'fecha_devolucion_real'])

    @staticmethod
    def list_prestamos_activos(rbd: int, limit: int = 50) -> list[dict]:
        """Lista préstamos activos del colegio para devolución rápida."""
        from backend.apps.core.models import PrestamoRecurso

        qs = (
            PrestamoRecurso.objects.filter(colegio_id=rbd, estado='ACTIVO')
            .select_related('recurso', 'usuario')
            .order_by('-fecha_prestamo')[:limit]
        )

        data = []
        for item in qs:
            data.append(
                {
                    'id': item.id_prestamo,
                    'recurso': item.recurso.titulo if item.recurso else 'Sin recurso',
                    'usuario': item.usuario.get_full_name() if item.usuario else 'Sin usuario',
                    'fecha_prestamo': str(item.fecha_prestamo),
                    'fecha_devolucion_esperada': str(item.fecha_devolucion_esperada),
                }
            )

        return data
