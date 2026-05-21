"""
Django settings for core project.

Migrado desde sistema_antiguo/core/settings.py
Compatible con estructura backend/apps/
"""

from pathlib import Path
import os
import sys
from datetime import timedelta
try:
    from distutils.util import strtobool
except ModuleNotFoundError:  # Python 3.12+ no incluye distutils
    def strtobool(value: str) -> int:
        normalized = str(value).strip().lower()
        if normalized in ('y', 'yes', 't', 'true', 'on', '1'):
            return 1
        if normalized in ('n', 'no', 'f', 'false', 'off', '0'):
            return 0
        raise ValueError(f'Invalid truth value: {value!r}')
from decouple import config


# Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR apunta a la raíz del proyecto (donde está manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


# Quick-start development settings - unsuitable for production
SECRET_KEY = config('SECRET_KEY')
_debug_raw = str(config('DEBUG', default='False'))
try:
    DEBUG = bool(strtobool(_debug_raw))
except ValueError:
    DEBUG = False
DEBUG_TOOLBAR_ENABLED = config('DEBUG_TOOLBAR_ENABLED', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,testserver').split(',')

API_ALLOWED_ORIGINS = config(
    'API_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173,http://localhost:5175,http://127.0.0.1:5175',
)
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in API_ALLOWED_ORIGINS.split(',') if origin.strip()]


# Application definition

INSTALLED_APPS = [
    # Django Channels debe ir ANTES de django.contrib.staticfiles
    'daphne',  # ASGI server para Channels
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # API
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',

    # Security Apps
    'axes',
    
    # Channels
    'channels',
    
    # Development Tools
    'django_extensions',

    # Apps migradas a backend.apps.*
    'backend.apps.accounts',
    'backend.apps.institucion',
    'backend.apps.cursos',
    'backend.apps.academico',
    'backend.apps.matriculas',
    'backend.apps.notificaciones',
    'backend.apps.mensajeria',
    'backend.apps.comunicados',
    'backend.apps.auditoria',  # Sistema de auditoría (Ley 20.370)
    'backend.apps.subscriptions',  # Sistema de suscripciones y monetización
    'backend.apps.core',  # Modelos mejorados Fase 3
    'backend.apps.security',  # Módulos de seguridad (hardening, sesiones, historial) 
]

# API v1 app (capa unificada REST)
INSTALLED_APPS.append('backend.apps.api')

if DEBUG and DEBUG_TOOLBAR_ENABLED:
    INSTALLED_APPS.append('debug_toolbar')

# CORS must be available for configured React origins even when an external
# DEBUG env var disables Django debug mode in local shells.
CORS_ENABLED = config('CORS_ENABLED', default='True' if CORS_ALLOWED_ORIGINS else 'False', cast=bool)
if CORS_ENABLED:
    INSTALLED_APPS.append('corsheaders')

PAYMENT_WEBHOOK_TOKEN = config('PAYMENT_WEBHOOK_TOKEN', default='')
PAYMENT_WEBHOOK_SECRET = config('PAYMENT_WEBHOOK_SECRET', default='')

AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'accounts:index'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'backend.apps.core.middleware.request_id.RequestIdMiddleware',
    'backend.apps.core.middleware.api_deprecation.ApiDeprecationHeadersMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'backend.common.subdomain_middleware.SubdomainMiddleware',
    'backend.apps.core.middleware.tenant.TenantMiddleware',
    
    # Middleware de suscripción (debe ir DESPUÉS de AuthenticationMiddleware)
    'backend.apps.subscriptions.middleware.SubscriptionMiddleware',
    
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Django-axes debe ir DESPUÉS de AuthenticationMiddleware
    'axes.middleware.AxesMiddleware',
    
    # Middleware de auditoría
    'backend.apps.auditoria.middleware.AuditoriaMiddleware',
    
    # Middleware de rendimiento (solo en DEBUG)
    'backend.apps.core.middleware.performance.QueryCountDebugMiddleware',
    'backend.apps.core.middleware.performance.SlowRequestLoggerMiddleware',
    'backend.apps.core.middleware.operational_metrics.OperationalMetricsMiddleware',
]

if CORS_ENABLED:
    # CORS debe ejecutarse justo después de SecurityMiddleware.
    MIDDLEWARE.insert(1, 'corsheaders.middleware.CorsMiddleware')

if DEBUG and DEBUG_TOOLBAR_ENABLED:
    MIDDLEWARE.insert(2, 'debug_toolbar.middleware.DebugToolbarMiddleware')

INTERNAL_IPS = config('INTERNAL_IPS', default='127.0.0.1,localhost').split(',')

ROOT_URLCONF = 'backend.apps.core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'frontend_django', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.apps.core.wsgi.application'

# ASGI Application para Django Channels (WebSocket)
ASGI_APPLICATION = 'backend.apps.core.routing.application'

# Configuración de Channel Layers
# Usar Redis en producción, InMemory en desarrollo
REDIS_URL = config('REDIS_URL', default=None)

if REDIS_URL:
    # Producción: Redis para escalabilidad
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    # Desarrollo: InMemory (solo para testing local)
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ============================================================================
# Tareas Asíncronas (Celery)
# ============================================================================
CELERY_BROKER_URL = REDIS_URL or 'memory://'
CELERY_RESULT_BACKEND = REDIS_URL or 'cache+memory://'

# Si no hay Redis configurado (ej: desarrollo local), ejecuta tareas síncronamente
if not REDIS_URL:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
else:
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'America/Santiago'



# Database
# Usar PostgreSQL en producción, SQLite en desarrollo
DATABASE_URL = config('DATABASE_URL', default=None)
DB_ENGINE = config('DB_ENGINE', default='sqlite')

if DATABASE_URL:
    # Producción: Usar DATABASE_URL (formato: postgresql://user:pass@host:port/dbname)
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif DB_ENGINE == 'postgresql':
    # Producción: PostgreSQL con variables individuales
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='colegio_db'),
            'USER': config('DB_USER', default='colegio_user'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 600,
            'CONN_HEALTH_CHECKS': True,
        }
    }
elif DB_ENGINE == 'mssql':
    # Alternativa: SQL Server (para Windows con AD auth)
    DATABASES = {
        'default': {
            'ENGINE': 'mssql',
            'NAME': config('DB_NAME', default='colegio_db'),
            'HOST': config('DB_HOST', default='localhost'),
            'USER': '',
            'PASSWORD': '',
            'OPTIONS': {
                'driver': 'ODBC Driver 17 for SQL Server',
                'extra_params': 'TrustServerCertificate=yes;Trusted_Connection=yes;',
            },
        }
    }
else:
    # Desarrollo: SQLite (solo para desarrollo local)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('username', 'email', 'nombre', 'apellido_paterno', 'apellido_materno'),
            'max_similarity': 0.5,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    # Validadores personalizados para seguridad reforzada
    {
        'NAME': 'backend.apps.accounts.validators.ComplexityPasswordValidator',
    },
    {
        'NAME': 'backend.apps.accounts.validators.NoRepeatingCharactersValidator',
        'OPTIONS': {
            'max_repeating': 2,
        }
    },
    {
        'NAME': 'backend.apps.accounts.validators.NoSpacesValidator',
    },
    {
        'NAME': 'backend.apps.accounts.validators.ChileanPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = config('LANGUAGE_CODE', default='es-cl')
TIME_ZONE = config('TIME_ZONE', default='America/Santiago')
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'frontend_django', 'static'),
    os.path.join(BASE_DIR, 'shared_assets'),
]

# Required for `python manage.py collectstatic`
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# File upload settings
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

# SEGURIDAD: Solo extensiones de archivos de negocio. Nunca permitir .py, .js, .html u otros ejecutables.
# Si necesitas ampliar esta lista, evaluar riesgos de seguridad primero.
ALLOWED_UPLOAD_EXTENSIONS = {
    # Documentos
    '.pdf', '.doc', '.docx', '.txt', '.odt', '.rtf',
    # Presentaciones
    '.ppt', '.pptx', '.odp',
    # Hojas de cálculo
    '.xls', '.xlsx', '.ods', '.csv',
    # Imágenes
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
    # Archivos comprimidos (solo formatos comunes)
    '.zip',
}

# SEGURIDAD: Solo MIME types seguros. Nunca text/html, application/javascript u otros ejecutables.
ALLOWED_MIME_TYPES = {
    # Documentos
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'application/vnd.oasis.opendocument.text',
    'application/rtf',
    # Presentaciones
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.oasis.opendocument.presentation',
    # Hojas de cálculo
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.oasis.opendocument.spreadsheet',
    'text/csv',
    # Imágenes
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'image/webp',
    # Archivos comprimidos
    'application/zip',
    'application/x-zip-compressed',
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email Configuration
# Usar SMTP en producción, Console en desarrollo
EMAIL_HOST = config('EMAIL_HOST', default=None)

if EMAIL_HOST:
    # Producción: SMTP real (ej: SendGrid, Gmail, AWS SES)
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = EMAIL_HOST
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=10, cast=int)
else:
    # Desarrollo: Console (imprime emails en terminal)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@colegio.cl')
SERVER_EMAIL = config('SERVER_EMAIL', default='root@localhost')

# Notificaciones transaccionales
NOTIFICATIONS_EMAIL_ENABLED = config('NOTIFICATIONS_EMAIL_ENABLED', default=True, cast=bool)

# Firebase Cloud Messaging (Push)
# En produccion debe definirse al menos uno de estos valores.
FCM_CREDENTIALS_FILE = config('FCM_CREDENTIALS_FILE', default='')
FCM_CREDENTIALS_JSON = config('FCM_CREDENTIALS_JSON', default='')


# ============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# ============================================================================

# Django-Axes: Protección contra fuerza bruta
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 hora
AXES_LOCK_OUT_AT_FAILURE = True
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = None
AXES_LOCKOUT_URL = None
AXES_VERBOSE = True
AXES_ENABLED = True
AXES_ENABLE_ACCESS_FAILURE_LOG = True
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]

# Configuración de Captcha (hCaptcha)
# SEGURIDAD: Nunca commitear las claves reales. Rotar inmediatamente si fueron expuestas.
HCAPTCHA_SITEKEY = config('HCAPTCHA_SITEKEY', default='')
HCAPTCHA_SECRET = config('HCAPTCHA_SECRET', default='')
HCAPTCHA_ENABLED = config('HCAPTCHA_ENABLED', default=False, cast=bool)

# Seguridad de Sesiones y Cookies
SESSION_COOKIE_SECURE = False  # True en producción con HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 3600 * 8  # 8 horas
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# CSRF Protection
CSRF_COOKIE_SECURE = False  # True en producción con HTTPS
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False
CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

# Seguridad General
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'


# ============================================================================
# API REST (DRF + JWT)
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'backend.apps.api.pagination.StandardCursorPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_VERSIONING_CLASS': 'backend.apps.api.versioning.QueryParamOrAcceptHeaderVersioning',
    'DEFAULT_VERSION': '1.0',
    'ALLOWED_VERSIONS': ['1.0'],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '120/min',
        'onboarding': '5/hour',
        'auth_token_burst': config('API_AUTH_TOKEN_BURST_RATE', default='10/min'),
        'auth_token_sustained': config('API_AUTH_TOKEN_SUSTAINED_RATE', default='60/hour'),
    },
}

API_DEPRECATION_MAP = {
    # Cuando se lance v2, cambiar `enabled` a True y definir fecha/doc.
    '1.0': {
        'enabled': config('API_V1_DEPRECATED', default=False, cast=bool),
        'sunset': config('API_V1_SUNSET', default=''),
        'doc_url': config('API_V1_DEPRECATION_DOC_URL', default=''),
        'message': config('API_V1_DEPRECATION_MESSAGE', default=''),
    }
}

API_IMAGE_UPLOAD_MAX_BYTES = config('API_IMAGE_UPLOAD_MAX_BYTES', default=8 * 1024 * 1024, cast=int)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS.copy()

# Dominio base para resolver subdominios tenant (ej: redpanda.cl).
TENANT_ROOT_DOMAIN = config('TENANT_ROOT_DOMAIN', default='')


# ============================================================================
# CONFIGURACIÓN DE CACHÉ Y RENDIMIENTO
# ============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache' if REDIS_URL else 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': REDIS_URL if REDIS_URL else 'unique-snowflake',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    },
    'template_cache': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'template-cache',
        'TIMEOUT': 600,
        'OPTIONS': {
            'MAX_ENTRIES': 500,
        }
    },
}

CACHE_TIMEOUT_SHORT = 60
CACHE_TIMEOUT_MEDIUM = 300
CACHE_TIMEOUT_LONG = 1800
CACHE_TIMEOUT_VERY_LONG = 3600

CONN_MAX_AGE = 600  # 10 minutos


# Configuración de Logging
WINDOWS_DISABLE_LOG_ROTATION = os.name == 'nt'
LOG_FILE_MAX_BYTES = 0 if WINDOWS_DISABLE_LOG_ROTATION else 1024 * 1024 * 10
LOG_ERRORS_BACKUP_COUNT = 0 if WINDOWS_DISABLE_LOG_ROTATION else 10
LOG_GENERAL_BACKUP_COUNT = 0 if WINDOWS_DISABLE_LOG_ROTATION else 5

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} [req:{request_id}] {name} {module}.{funcName}:{lineno} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {asctime} [req:{request_id}] - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'request_id': {
            '()': 'backend.apps.core.logging_filters.RequestIdLogFilter',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['require_debug_true', 'request_id'],
        },
        'file_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
            # En Windows, el rename de rollover puede fallar con WinError 32
            # cuando el archivo está abierto por otro proceso/hilo.
            'maxBytes': LOG_FILE_MAX_BYTES,
            'backupCount': LOG_ERRORS_BACKUP_COUNT,
            'formatter': 'verbose',
            'filters': ['request_id'],
        },
        'file_general': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'general.log'),
            'maxBytes': LOG_FILE_MAX_BYTES,
            'backupCount': LOG_GENERAL_BACKUP_COUNT,
            'formatter': 'verbose',
            'filters': ['request_id'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_general', 'file_errors'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file_errors'],
            'level': 'ERROR',
            'propagate': False,
        },
        'backend.apps': {
            'handlers': ['console', 'file_general', 'file_errors'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Crear directorio de logs si no existe
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Configuraciones HTTPS para producción.
# Se activan solo cuando el entorno lo solicita explícitamente para no romper
# el login por API en desarrollo local sobre HTTP.
if config('SECURE_SSL_REDIRECT', default=False, cast=bool):
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Test settings
if 'test' in sys.argv:
    # Disable custom password validators for tests
    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
            'OPTIONS': {
                'min_length': 1,  # Very short for tests
            }
        },
    ]
