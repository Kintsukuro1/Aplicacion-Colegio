"""
Formularios para el wizard de configuraciÃ³n inicial del colegio.

Implementa validaciÃ³n robusta para todos los pasos del setup wizard,
incluyendo validaciÃ³n de contraseÃ±as, emails, RUTs y datos de negocio.
"""
from datetime import date
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, MinLengthValidator
import re

from backend.apps.institucion.models import Colegio, CicloAcademico, NivelEducativo
from backend.apps.cursos.models import Curso

User = get_user_model()
USER_HAS_USERNAME_FIELD = any(field.name == 'username' for field in User._meta.get_fields())

def _build_temp_user_for_password(username_value='', email_value=''):
    """Crea un usuario temporal compatible con modelos sin campo username."""
    if USER_HAS_USERNAME_FIELD:
        return User(username=username_value or '', email=email_value or '')
    user = User(email=email_value or '')
    # Compatibilidad con validadores legacy que asumen atributo `username`.
    user.username = username_value or ''
    return user


class CicloAcademicoForm(forms.Form):
    """Formulario para crear ciclo acadÃ©mico (Paso 1 del wizard)"""
    
    nombre = forms.CharField(
        max_length=100,
        required=True,
        label="Nombre del Ciclo",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Ciclo Escolar 2026'
        }),
        help_text="IdentificaciÃ³n del perÃ­odo acadÃ©mico"
    )
    
    anio = forms.IntegerField(
        required=True,
        label="AÃ±o",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '2026'
        }),
        help_text="AÃ±o del ciclo acadÃ©mico"
    )
    
    fecha_inicio = forms.DateField(
        required=True,
        label="Fecha de Inicio",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Fecha de inicio del ciclo escolar"
    )
    
    fecha_fin = forms.DateField(
        required=True,
        label="Fecha de Fin",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Fecha de tÃ©rmino del ciclo escolar"
    )
    
    def clean_anio(self):
        """Validar que el aÃ±o sea vÃ¡lido"""
        anio = self.cleaned_data.get('anio')
        current_year = date.today().year
        
        if anio < 2020 or anio > current_year + 2:
            raise ValidationError(
                f"El aÃ±o debe estar entre 2020 y {current_year + 2}"
            )
        
        return anio
    
    def clean(self):
        """ValidaciÃ³n cruzada de fechas"""
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin:
            if fecha_inicio >= fecha_fin:
                raise ValidationError(
                    "La fecha de inicio debe ser anterior a la fecha de fin"
                )
            
            # Validar duraciÃ³n mÃ­nima (6 meses)
            duracion_dias = (fecha_fin - fecha_inicio).days
            if duracion_dias < 180:
                raise ValidationError(
                    "El ciclo acadÃ©mico debe tener una duraciÃ³n mÃ­nima de 6 meses"
                )
        
        return cleaned_data


class CursoCreationForm(forms.Form):
    """Formulario para crear cursos (Paso 2 del wizard)"""
    
    nivel = forms.ModelChoiceField(
        queryset=NivelEducativo.objects.all(),
        required=True,
        label="Nivel Educativo",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Seleccione el nivel educativo"
    )
    
    grado = forms.IntegerField(
        required=True,
        label="Grado",
        min_value=1,
        max_value=8,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 1'
        }),
        help_text="Grado del curso (1-8)"
    )
    
    letra = forms.CharField(
        max_length=1,
        required=True,
        label="Letra del Curso",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'A',
            'maxlength': '1'
        }),
        help_text="Letra identificadora del curso (A, B, C, etc.)"
    )
    
    cantidad = forms.IntegerField(
        required=False,
        initial=1,
        min_value=1,
        max_value=10,
        label="Cantidad de Cursos Paralelos",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '1'
        }),
        help_text="NÃºmero de cursos paralelos a crear (letras consecutivas)"
    )
    
    def clean_letra(self):
        """Validar que la letra sea vÃ¡lida"""
        letra = self.cleaned_data.get('letra', '').upper()
        
        if not letra.isalpha():
            raise ValidationError("La letra debe ser un carÃ¡cter alfabÃ©tico")
        
        if not 'A' <= letra <= 'Z':
            raise ValidationError("La letra debe estar entre A y Z")
        
        return letra


class ProfesorCreationForm(forms.Form):
    """Formulario para crear profesores (Paso 3 del wizard)"""
    
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Nombre de Usuario",
        validators=[MinLengthValidator(4)],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'profesor.apellido',
            'autocomplete': 'off'
        }),
        help_text="MÃ­nimo 4 caracteres. Solo letras, nÃºmeros y . _ -"
    )
    
    email = forms.EmailField(
        required=True,
        label="Correo ElectrÃ³nico",
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'profesor@colegio.cl'
        }),
        help_text="Correo electrÃ³nico institucional del profesor"
    )
    
    rut = forms.CharField(
        max_length=12,
        required=True,
        label="RUT",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345678-9'
        }),
        help_text="RUT con guiÃ³n (ej: 12345678-9)"
    )
    
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Nombre",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Juan'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Apellido",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'PÃ©rez GonzÃ¡lez'
        })
    )
    
    password = forms.CharField(
        required=True,
        label="ContraseÃ±a",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
        help_text="MÃ­nimo 12 caracteres con mayÃºsculas, minÃºsculas, nÃºmeros y sÃ­mbolos"
    )
    
    password_confirm = forms.CharField(
        required=True,
        label="Confirmar ContraseÃ±a",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        })
    )
    
    def __init__(self, *args, rbd_colegio=None, **kwargs):
        self.rbd_colegio = rbd_colegio
        super().__init__(*args, **kwargs)
    
    def clean_username(self):
        """Validar username Ãºnico y formato"""
        username = self.cleaned_data.get('username') or ''
        
        # Validar formato (solo letras, nÃºmeros y _ . -)
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            raise ValidationError(
                "El nombre de usuario solo puede contener letras, nÃºmeros y los caracteres . _ -"
            )
        
        # Verificar unicidad
        if USER_HAS_USERNAME_FIELD and User.objects.filter(username=username).exists():
            raise ValidationError(
                "Este nombre de usuario ya estÃ¡ en uso. Por favor, elige otro."
            )
        
        return username.lower()
    
    def clean_email(self):
        """Validar email Ãºnico"""
        email = self.cleaned_data.get('email')
        
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                "Este correo electrÃ³nico ya estÃ¡ registrado. Por favor, usa otro."
            )
        
        return email.lower()
    
    def clean_rut(self):
        """Validar formato y unicidad del RUT"""
        rut = self.cleaned_data.get('rut')
        
        # Normalizar formato
        rut = rut.replace('.', '').replace(' ', '').strip()
        
        # Validar formato bÃ¡sico (nnnnnnnn-d)
        if not re.match(r'^\d{7,8}-[0-9Kk]$', rut):
            raise ValidationError(
                "Formato de RUT invÃ¡lido. Debe ser: 12345678-9"
            )
        
        # Verificar unicidad
        if User.objects.filter(rut=rut).exists():
            raise ValidationError(
                "Este RUT ya estÃ¡ registrado en el sistema."
            )
        
        # Validar dÃ­gito verificador
        rut_numeros, dv_ingresado = rut.split('-')
        dv_calculado = self._calcular_dv(rut_numeros)
        
        if dv_calculado.upper() != dv_ingresado.upper():
            raise ValidationError(
                "El dÃ­gito verificador del RUT es invÃ¡lido."
            )
        
        return rut
    
    def _calcular_dv(self, rut_sin_dv):
        """Calcular dÃ­gito verificador del RUT chileno"""
        suma = 0
        multiplo = 2
        
        for digito in reversed(rut_sin_dv):
            suma += int(digito) * multiplo
            multiplo = multiplo + 1 if multiplo < 7 else 2
        
        resto = suma % 11
        dv = 11 - resto
        
        if dv == 11:
            return '0'
        elif dv == 10:
            return 'K'
        else:
            return str(dv)
    
    def clean_password(self):
        """Validar contraseÃ±a usando los validadores de Django"""
        password = self.cleaned_data.get('password')
        
        # Django ejecutarÃ¡ automÃ¡ticamente los validadores en AUTH_PASSWORD_VALIDATORS
        # incluyendo nuestros validadores personalizados
        from django.contrib.auth.password_validation import validate_password
        
        # Crear un usuario temporal para validaciÃ³n
        temp_user = _build_temp_user_for_password(
            username_value=self.cleaned_data.get('username', ''),
            email_value=self.cleaned_data.get('email', ''),
        )
        
        try:
            validate_password(password, user=temp_user)
        except ValidationError as e:
            raise ValidationError(e.messages)
        
        return password
    
    def clean(self):
        """ValidaciÃ³n cruzada: contraseÃ±as coinciden"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise ValidationError({
                    'password_confirm': "Las contraseÃ±as no coinciden"
                })
        
        return cleaned_data


class EstudianteApoderadoForm(forms.Form):
    """Formulario para crear estudiante y apoderado (Paso 4 del wizard)"""
    
    # Campos del Apoderado
    apoderado_username = forms.CharField(
        max_length=150,
        required=True,
        label="Usuario del Apoderado",
        validators=[MinLengthValidator(4)],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'apoderado.apellido'
        })
    )
    
    apoderado_email = forms.EmailField(
        required=True,
        label="Email del Apoderado",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'apoderado@email.cl'
        })
    )
    
    apoderado_rut = forms.CharField(
        max_length=12,
        required=True,
        label="RUT del Apoderado",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345678-9'
        })
    )
    
    apoderado_first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Nombre del Apoderado",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    apoderado_last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Apellido del Apoderado",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    apoderado_password = forms.CharField(
        required=True,
        label="ContraseÃ±a del Apoderado",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    apoderado_password_confirm = forms.CharField(
        required=True,
        label="Confirmar ContraseÃ±a",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    # Campos del Estudiante
    estudiante_username = forms.CharField(
        max_length=150,
        required=True,
        label="Usuario del Estudiante",
        validators=[MinLengthValidator(4)],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'estudiante.apellido'
        })
    )
    
    estudiante_email = forms.EmailField(
        required=False,
        label="Email del Estudiante",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'estudiante@email.cl (opcional)'
        }),
        help_text="Opcional para estudiantes menores"
    )
    
    estudiante_rut = forms.CharField(
        max_length=12,
        required=True,
        label="RUT del Estudiante",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345678-9'
        })
    )
    
    estudiante_first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Nombre del Estudiante",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    estudiante_last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Apellido del Estudiante",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    estudiante_password = forms.CharField(
        required=True,
        label="ContraseÃ±a del Estudiante",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    estudiante_password_confirm = forms.CharField(
        required=True,
        label="Confirmar ContraseÃ±a",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    # RelaciÃ³n
    parentesco = forms.ChoiceField(
        required=True,
        label="Parentesco",
        choices=[
            ('padre', 'Padre'),
            ('madre', 'Madre'),
            ('abuelo', 'Abuelo/a'),
            ('tio', 'TÃ­o/a'),
            ('tutor', 'Tutor Legal'),
            ('otro', 'Otro')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, rbd_colegio=None, **kwargs):
        self.rbd_colegio = rbd_colegio
        super().__init__(*args, **kwargs)
    
    def clean_apoderado_username(self):
        """Validar username del apoderado"""
        username = self.cleaned_data.get('apoderado_username') or ''
        
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            raise ValidationError(
                "El nombre de usuario solo puede contener letras, nÃºmeros y . _ -"
            )
        
        if USER_HAS_USERNAME_FIELD and User.objects.filter(username=username).exists():
            raise ValidationError("Este nombre de usuario ya estÃ¡ en uso")
        
        return username.lower()
    
    def clean_apoderado_email(self):
        """Validar email del apoderado"""
        email = self.cleaned_data.get('apoderado_email')
        
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este correo ya estÃ¡ registrado")
        
        return email.lower()
    
    def clean_apoderado_rut(self):
        """Validar RUT del apoderado"""
        return self._validate_and_clean_rut(self.cleaned_data.get('apoderado_rut'))
    
    def clean_estudiante_username(self):
        """Validar username del estudiante"""
        username = self.cleaned_data.get('estudiante_username') or ''
        
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            raise ValidationError(
                "El nombre de usuario solo puede contener letras, nÃºmeros y . _ -"
            )
        
        if USER_HAS_USERNAME_FIELD and User.objects.filter(username=username).exists():
            raise ValidationError("Este nombre de usuario ya estÃ¡ en uso")
        
        return username.lower()
    
    def clean_estudiante_email(self):
        """Validar email del estudiante (opcional)"""
        email = self.cleaned_data.get('estudiante_email')
        
        if email:
            if User.objects.filter(email=email).exists():
                raise ValidationError("Este correo ya estÃ¡ registrado")
            return email.lower()
        
        return email
    
    def clean_estudiante_rut(self):
        """Validar RUT del estudiante"""
        return self._validate_and_clean_rut(self.cleaned_data.get('estudiante_rut'))
    
    def _validate_and_clean_rut(self, rut):
        """Validar y limpiar RUT (reutilizable)"""
        if not rut:
            return rut
        
        rut = rut.replace('.', '').replace(' ', '').strip()
        
        if not re.match(r'^\d{7,8}-[0-9Kk]$', rut):
            raise ValidationError("Formato de RUT invÃ¡lido. Debe ser: 12345678-9")
        
        if User.objects.filter(rut=rut).exists():
            raise ValidationError("Este RUT ya estÃ¡ registrado")
        
        # Validar dÃ­gito verificador
        rut_numeros, dv_ingresado = rut.split('-')
        dv_calculado = self._calcular_dv(rut_numeros)
        
        if dv_calculado.upper() != dv_ingresado.upper():
            raise ValidationError("El dÃ­gito verificador del RUT es invÃ¡lido")
        
        return rut
    
    def _calcular_dv(self, rut_sin_dv):
        """Calcular dÃ­gito verificador del RUT"""
        suma = 0
        multiplo = 2
        
        for digito in reversed(rut_sin_dv):
            suma += int(digito) * multiplo
            multiplo = multiplo + 1 if multiplo < 7 else 2
        
        resto = suma % 11
        dv = 11 - resto
        
        if dv == 11:
            return '0'
        elif dv == 10:
            return 'K'
        else:
            return str(dv)
    
    def clean(self):
        """Validaciones cruzadas"""
        cleaned_data = super().clean()
        
        # Validar contraseÃ±as del apoderado
        apod_pass = cleaned_data.get('apoderado_password')
        apod_confirm = cleaned_data.get('apoderado_password_confirm')
        
        if apod_pass and apod_confirm and apod_pass != apod_confirm:
            raise ValidationError({
                'apoderado_password_confirm': "Las contraseÃ±as del apoderado no coinciden"
            })
        
        # Validar contraseÃ±as del estudiante
        est_pass = cleaned_data.get('estudiante_password')
        est_confirm = cleaned_data.get('estudiante_password_confirm')
        
        if est_pass and est_confirm and est_pass != est_confirm:
            raise ValidationError({
                'estudiante_password_confirm': "Las contraseÃ±as del estudiante no coinciden"
            })
        
        # Validar que apoderado y estudiante no tengan el mismo RUT
        apod_rut = cleaned_data.get('apoderado_rut')
        est_rut = cleaned_data.get('estudiante_rut')
        
        if apod_rut and est_rut and apod_rut == est_rut:
            raise ValidationError(
                "El apoderado y el estudiante no pueden tener el mismo RUT"
            )
        
        # Validar contraseÃ±as con validadores de Django
        from django.contrib.auth.password_validation import validate_password
        
        if apod_pass:
            try:
                temp_user = _build_temp_user_for_password(
                    username_value=cleaned_data.get('apoderado_username', ''),
                    email_value=cleaned_data.get('apoderado_email', ''),
                )
                validate_password(apod_pass, user=temp_user)
            except ValidationError as e:
                raise ValidationError({
                    'apoderado_password': f"ContraseÃ±a del apoderado: {', '.join(e.messages)}"
                })
        
        if est_pass:
            try:
                temp_user = _build_temp_user_for_password(
                    username_value=cleaned_data.get('estudiante_username', ''),
                    email_value=cleaned_data.get('estudiante_email', ''),
                )
                validate_password(est_pass, user=temp_user)
            except ValidationError as e:
                raise ValidationError({
                    'estudiante_password': f"ContraseÃ±a del estudiante: {', '.join(e.messages)}"
                })
        
        return cleaned_data

