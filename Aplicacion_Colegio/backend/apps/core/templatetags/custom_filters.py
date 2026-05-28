from django import template

register = template.Library()

# Misma paleta que mensajería / asistencia apoderado (por nombre de materia).
_SUBJECT_ACCENT_RULES = (
    ('matem', '#3B82F6'),
    ('lengua', '#EF4444'),
    ('comunic', '#EF4444'),
    ('castellano', '#EF4444'),
    ('cienc', '#10B981'),
    ('natur', '#10B981'),
    ('biolog', '#10B981'),
    ('histor', '#8B5CF6'),
    ('geograf', '#8B5CF6'),
    ('ingl', '#F59E0B'),
    ('english', '#F59E0B'),
    ('edfis', '#06B6D4'),
    ('educación física', '#06B6D4'),
    ('educacion fisica', '#06B6D4'),
    ('deport', '#06B6D4'),
    ('músic', '#F97316'),
    ('music', '#F97316'),
    ('musica', '#F97316'),
    ('música', '#F97316'),
    ('arte', '#EC4899'),
    ('visual', '#EC4899'),
    ('tecno', '#6B7280'),
    ('comput', '#6B7280'),
    ('tecnología', '#6B7280'),
    ('tecnologia', '#6B7280'),
    ('religion', '#A855F7'),
    ('religión', '#A855F7'),
)


@register.filter
def count_estado(items, estado):
    """Cuenta ítems con un valor de estado (pagos, cuotas, etc.)."""
    if not items:
        return 0
    target = (estado or '').upper()
    return sum(1 for item in items if (getattr(item, 'estado', '') or '').upper() == target)


@register.filter
def pesos_cl(value):
    """Formato moneda chilena: $ 50.000"""
    try:
        n = int(float(value or 0))
        return '$ ' + f'{n:,}'.replace(',', '.')
    except (TypeError, ValueError):
        return '$ 0'


@register.filter
def color_asignatura(nombre, model_color=None):
    """Color de borde/texto según el nombre de la asignatura."""
    subject = (nombre or '').lower()
    for key, accent in _SUBJECT_ACCENT_RULES:
        if key in subject:
            return accent
    color = (str(model_color).strip() if model_color else '') or ''
    if color and color.lower() not in ('#667eea',):
        return color
    return '#64748b'


@register.filter
def asignaturas_unicas(clases):
    """
    Toma un queryset de clases y devuelve una lista de nombres de asignaturas únicos,
    separados por comas.
    """
    if not clases:
        return "Sin asignaturas"

    asignaturas = set()
    for clase in clases:
        if clase.activo and clase.asignatura:
            asignaturas.add(clase.asignatura.nombre)

    if asignaturas:
        return ", ".join(sorted(asignaturas))
    else:
        return "Sin asignaturas"