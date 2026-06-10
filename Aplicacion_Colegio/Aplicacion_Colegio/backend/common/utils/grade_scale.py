"""
Utilidad centralizada para obtener la escala de notas de un colegio.

Todas las comparaciones de aprobación/reprobación y validaciones de rango
deben pasar por este módulo para respetar la configuración por colegio.

Escala por defecto (Chile): 1.0 - 7.0, aprobación 4.0, 1 decimal.
"""
from decimal import Decimal
from functools import lru_cache
from typing import Optional, Dict, Any


# Defaults chilenos — se usan si el colegio no tiene ConfiguracionAcademica
_DEFAULTS = {
    'nota_minima': Decimal('1.0'),
    'nota_maxima': Decimal('7.0'),
    'nota_aprobacion': Decimal('4.0'),
    'redondeo_decimales': 1,
}


def get_escala(colegio) -> Dict[str, Any]:
    """
    Retorna la escala de notas configurada para un colegio.
    Si no existe ConfiguracionAcademica, retorna defaults chilenos.

    Args:
        colegio: instancia de Colegio, o None

    Returns:
        dict con keys: nota_minima, nota_maxima, nota_aprobacion, redondeo_decimales
    """
    if colegio is None:
        return _DEFAULTS.copy()

    from backend.apps.institucion.models import ConfiguracionAcademica
    return ConfiguracionAcademica.get_escala_para_colegio(colegio)


def es_aprobado(nota: float, colegio=None) -> bool:
    """Determina si una nota es aprobatoria según la escala del colegio."""
    escala = get_escala(colegio)
    return nota >= float(escala['nota_aprobacion'])


def estado_nota(nota: Optional[float], colegio=None) -> str:
    """Retorna 'Aprobado', 'Reprobado' o 'Sin notas' según la escala del colegio."""
    if nota is None:
        return 'Sin notas'
    return 'Aprobado' if es_aprobado(nota, colegio) else 'Reprobado'


def en_rango(nota: float, colegio=None) -> bool:
    """Verifica si una nota está dentro del rango válido de la escala."""
    escala = get_escala(colegio)
    return float(escala['nota_minima']) <= nota <= float(escala['nota_maxima'])


def redondear_nota(nota: float, colegio=None) -> float:
    """Redondea una nota según la configuración del colegio."""
    escala = get_escala(colegio)
    return round(nota, escala['redondeo_decimales'])


def normalize_grade_value(value: Any) -> Optional[Decimal]:
    """
    Normaliza el valor de una calificación. Si es mayor a 10 (ej. 65),
    la divide por 10 (ej. 6.5) para soportar datos heredados o de importaciones.
    """
    if value is None:
        return None
    try:
        val = Decimal(str(value))
        if abs(val) > 10:
            val = val / Decimal('10.0')
        return val
    except Exception:
        return value

