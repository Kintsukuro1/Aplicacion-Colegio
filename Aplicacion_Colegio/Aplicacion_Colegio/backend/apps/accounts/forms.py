"""Formularios del módulo accounts.

Migrado desde `sistema_antiguo/accounts/forms.py` para evitar hacks de sys.path.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

import re


class SecureLoginForm(forms.Form):
    """Formulario de login seguro con validaciones adicionales."""

    username = forms.CharField(
        max_length=254,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email o RUT",
                "autocomplete": "username",
                "aria-label": "Usuario",
            }
        ),
        label="Usuario (Email o RUT)",
        error_messages={
            "required": "Por favor ingresa tu usuario.",
            "max_length": "El usuario no puede exceder 254 caracteres.",
        },
    )

    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Contraseña",
                "autocomplete": "current-password",
                "aria-label": "Contraseña",
            }
        ),
        label="Contraseña",
        error_messages={
            "required": "Por favor ingresa tu contraseña.",
        },
    )

    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Mantener sesión iniciada",
    )

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()

        sql_keywords = [
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "UNION",
            "OR 1=1",
            "OR 1",
            "--",
            ";--",
            "xp_",
            "sp_",
            "<script",
            "javascript:",
            "onerror=",
            "onload=",
        ]

        username_upper = username.upper()
        for keyword in sql_keywords:
            if keyword in username_upper:
                raise ValidationError(
                    _("El usuario contiene caracteres o patrones no permitidos."),
                    code="invalid_characters",
                )

        if len(username) > 254:
            raise ValidationError(
                _("El nombre de usuario es demasiado largo."),
                code="username_too_long",
            )

        dangerous_chars = ["<", ">", "{", "}", "|", "\\", "^", "~", "[", "]", "`"]
        for char in dangerous_chars:
            if char in username:
                raise ValidationError(
                    _("El usuario contiene caracteres no permitidos."),
                    code="invalid_characters",
                )

        if "@" in username:
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, username):
                raise ValidationError(_("El formato del email no es válido."), code="invalid_email")

        if "-" in username and any(char.isdigit() for char in username):
            rut_pattern = r"^\d{1,2}\.\d{3}\.\d{3}-[\dkK]$"
            if not re.match(rut_pattern, username):
                raise ValidationError(
                    _("El formato del RUT no es válido (Ej: 12.345.678-9)."),
                    code="invalid_rut",
                )

        return username

    def clean_password(self):
        password = self.cleaned_data.get("password") or ""

        sql_keywords = [
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "UNION",
            "OR 1=1",
            "--",
            ";--",
            "<script",
            "javascript:",
        ]

        password_upper = password.upper()
        for keyword in sql_keywords:
            if keyword in password_upper:
                raise ValidationError(_("La contraseña contiene patrones no permitidos."), code="invalid_password")

        if len(password) > 128:
            raise ValidationError(_("La contraseña es demasiado larga."), code="password_too_long")

        return password

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if username and password and username.lower() == password.lower():
            raise ValidationError(
                _("La contraseña no puede ser igual al nombre de usuario."),
                code="password_equals_username",
            )

        return cleaned_data
