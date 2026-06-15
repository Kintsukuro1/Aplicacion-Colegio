"""
Validadores compartidos para todo el sistema
"""
import re
from django.core.exceptions import ValidationError


def validar_rut_chileno(rut):
    """
    Valida formato y dígito verificador de RUT chileno
    
    Args:
        rut (str): RUT en formato XX.XXX.XXX-X o XXXXXXXX-X
        
    Raises:
        ValidationError: Si el RUT es inválido
    """
    # Eliminar puntos y guiones
    rut_limpio = rut.replace(".", "").replace("-", "")
    
    if len(rut_limpio) < 2:
        raise ValidationError("RUT debe tener al menos 2 caracteres")
    
    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1].upper()
    
    # Validar que el cuerpo sea numérico
    if not cuerpo.isdigit():
        raise ValidationError("RUT debe contener solo números")
    
    # Calcular dígito verificador
    suma = 0
    multiplo = 2
    
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplo
        multiplo += 1
        if multiplo == 8:
            multiplo = 2
    
    dv_calculado = 11 - (suma % 11)
    
    if dv_calculado == 11:
        dv_esperado = '0'
    elif dv_calculado == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(dv_calculado)
    
    if dv != dv_esperado:
        raise ValidationError(f"Dígito verificador inválido. Esperado: {dv_esperado}")
    
    return True


def validar_email_institucional(email, dominio=None):
    """
    Valida que el email tenga formato correcto y opcionalmente un dominio específico
    
    Args:
        email (str): Email a validar
        dominio (str, optional): Dominio requerido (ej: 'colegio.cl')
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        raise ValidationError("Formato de email inválido")
    
    if dominio and not email.endswith(f"@{dominio}"):
        raise ValidationError(f"Email debe ser del dominio {dominio}")
    
    return True


def validar_telefono_chileno(telefono):
    """
    Valida formato de teléfono chileno (+56 9 XXXX XXXX o 9 XXXX XXXX)
    
    Args:
        telefono (str): Número de teléfono
    """
    # Eliminar espacios, guiones y paréntesis
    telefono_limpio = re.sub(r'[\s\-\(\)]', '', telefono)
    
    # Eliminar prefijo +56 si existe
    if telefono_limpio.startswith('+56'):
        telefono_limpio = telefono_limpio[3:]
    elif telefono_limpio.startswith('56'):
        telefono_limpio = telefono_limpio[2:]
    
    # Debe empezar con 9 y tener 9 dígitos
    pattern = r'^9\d{8}$'
    
    if not re.match(pattern, telefono_limpio):
        raise ValidationError("Teléfono debe tener formato: 9 XXXX XXXX")
    
    return True
