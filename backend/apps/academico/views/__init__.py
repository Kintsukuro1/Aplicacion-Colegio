"""Academico views package.

Durante la migración, evitamos imports en cascada desde aquí porque algunos
módulos aún dependen de `sistema_antiguo.*`. Importa directamente el submódulo
que necesites (p.ej. `backend.apps.academico.views.student_detail_views`).
"""

__all__ = []
