"""Paleta institucional de colores por nombre de asignatura."""

SUBJECT_ACCENT_RULES = (
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


def resolve_asignatura_color(nombre, model_color=None):
    """Devuelve el color canónico según el nombre; usa model_color como respaldo."""
    subject = (nombre or '').lower()
    for key, accent in SUBJECT_ACCENT_RULES:
        if key in subject:
            return accent
    color = (str(model_color).strip() if model_color else '') or ''
    if color and color.lower() not in ('#667eea',):
        return color
    return '#64748b'
