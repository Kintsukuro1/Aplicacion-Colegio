"""
Custom Password Validators for Enhanced Security

Implements additional password validation beyond Django's built-in validators
to ensure strong, secure passwords for all users in the school management system.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityPasswordValidator:
    """
    Validates that the password meets complexity requirements:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("La contraseña debe contener al menos una letra mayúscula."),
                code='password_no_upper',
            )
        
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("La contraseña debe contener al menos una letra minúscula."),
                code='password_no_lower',
            )
        
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _("La contraseña debe contener al menos un número."),
                code='password_no_digit',
            )
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;`~]', password):
            raise ValidationError(
                _("La contraseña debe contener al menos un carácter especial (!@#$%^&*(),.?\":{}|<>_-+=[]\\\/;`~)."),
                code='password_no_special',
            )
    
    def get_help_text(self):
        return _(
            "Tu contraseña debe contener al menos una mayúscula, una minúscula, "
            "un número y un carácter especial."
        )


class NoRepeatingCharactersValidator:
    """
    Validates that the password doesn't contain too many repeating characters.
    Prevents passwords like 'aaa111' or 'password!!!!'
    """
    
    def __init__(self, max_repeating=2):
        """
        Args:
            max_repeating: Maximum number of consecutive identical characters allowed
        """
        self.max_repeating = max_repeating
    
    def validate(self, password, user=None):
        # Check for consecutive repeating characters
        pattern = r'(.)\1{' + str(self.max_repeating) + ',}'
        if re.search(pattern, password):
            raise ValidationError(
                _(f"La contraseña no puede contener más de {self.max_repeating} caracteres idénticos consecutivos."),
                code='password_too_many_repeating',
            )
    
    def get_help_text(self):
        return _(
            f"Tu contraseña no puede contener más de {self.max_repeating} "
            f"caracteres idénticos consecutivos."
        )


class NoSpacesValidator:
    """
    Validates that the password doesn't contain spaces.
    Spaces can cause issues with some systems and are generally not recommended.
    """
    
    def validate(self, password, user=None):
        if ' ' in password:
            raise ValidationError(
                _("La contraseña no puede contener espacios."),
                code='password_contains_spaces',
            )
    
    def get_help_text(self):
        return _("Tu contraseña no puede contener espacios.")


class ChileanPasswordValidator:
    """
    Validates against common weak patterns specific to Chilean context:
    - Common Chilean names
    - Sequential patterns (123456, abcdef)
    - Keyboard patterns (qwerty, asdfgh)
    - Common words in Spanish
    """
    
    # Common weak patterns
    WEAK_PATTERNS = [
        # Sequential
        '123456', '654321', 'abcdef', 'fedcba',
        '1234567', '7654321', 'abcdefg', 'gfedcba',
        '12345678', '87654321', 'abcdefgh', 'hgfedcba',
        
        # Keyboard patterns
        'qwerty', 'qwertyui', 'asdfgh', 'asdfghjk', 'zxcvbn', 'zxcvbnm',
        
        # Common Spanish words (lowercase variations checked automatically)
        'password', 'contraseña', 'clave', 'admin', 'administrador',
        'usuario', 'colegio', 'escuela', 'profesor', 'estudiante',
        'apoderado', 'chile', 'santiago',
    ]
    
    def validate(self, password, user=None):
        password_lower = password.lower()
        
        # Check against weak patterns
        for pattern in self.WEAK_PATTERNS:
            if pattern in password_lower:
                raise ValidationError(
                    _("La contraseña contiene un patrón común inseguro. Por favor, elige una contraseña más única."),
                    code='password_too_common',
                )
        
        # Check if password is just a year (common weak password)
        if re.match(r'^(19|20)\d{2}$', password):
            raise ValidationError(
                _("La contraseña no puede ser solo un año."),
                code='password_is_year',
            )
        
        # Check for user-specific weak passwords if user is provided
        if user:
            # Check against username
            if user.username and len(user.username) >= 3:
                if user.username.lower() in password_lower:
                    raise ValidationError(
                        _("La contraseña no puede contener tu nombre de usuario."),
                        code='password_contains_username',
                    )
            
            # Check against email
            if user.email:
                email_parts = user.email.split('@')[0].lower()
                if len(email_parts) >= 3 and email_parts in password_lower:
                    raise ValidationError(
                        _("La contraseña no puede contener tu correo electrónico."),
                        code='password_contains_email',
                    )
            
            # Check against name components
            if hasattr(user, 'nombre') and user.nombre:
                if len(user.nombre) >= 3 and user.nombre.lower() in password_lower:
                    raise ValidationError(
                        _("La contraseña no puede contener tu nombre."),
                        code='password_contains_name',
                    )
    
    def get_help_text(self):
        return _(
            "Tu contraseña no puede contener patrones comunes, secuencias simples, "
            "tu nombre de usuario, correo electrónico o nombre real."
        )
