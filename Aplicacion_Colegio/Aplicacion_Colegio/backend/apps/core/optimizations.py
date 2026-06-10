"""
Core optimizations for performance-critical queries
"""

from backend.apps.cursos.models import Clase


def get_clases_profesor_optimized(rbd_colegio, profesor_id):
    """
    Get active classes for a teacher with optimized query

    Args:
        rbd_colegio: School RBD
        profesor_id: Teacher user ID

    Returns:
        QuerySet of active Clase objects for the teacher
    """
    return Clase.objects.filter(
        colegio__rbd=rbd_colegio,
        profesor_id=profesor_id,
        activo=True
    ).select_related(
        'asignatura',
        'curso',
        'colegio'
    ).order_by(
        'curso__nivel__nombre',
        'curso__nombre',
        'asignatura__nombre'
    )