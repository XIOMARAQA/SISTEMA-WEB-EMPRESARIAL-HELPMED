"""
Django settings for HelpMed — Seguricel S.A.C.
Python 3.13 | Django 5.2 | PostgreSQL 18
Todas las variables sensibles se cargan desde backend/.env
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ('true', '1', 'yes', 'on')


def env_list(key: str, default: str = '') -> list[str]:
    raw = os.getenv(key, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


def env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('SECRET_KEY no definida. Copie backend/.env.example a backend/.env')

DEBUG = env_bool('DEBUG', False)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'seguridad',
    'logistica',
    'calidad',
    'ambiental',
    'inventario',
    'riesgos',
    'auditoria',
    'notificaciones',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'auditoria.middleware.AuditoriaMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

_db_schema = os.getenv('DB_SCHEMA', 'public').strip()
_db_options = {}
if _db_schema and _db_schema != 'public':
    _db_options['options'] = f'-c search_path={_db_schema}'

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', 'helpmed'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        **({'OPTIONS': _db_options} if _db_options else {}),
    }
}

AUTH_USER_MODEL = 'seguridad.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'es-pe')
TIME_ZONE = os.getenv('TIME_ZONE', 'America/Lima')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': env_int('PAGE_SIZE', 20),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=env_int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 60)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=env_int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7)),
    'ROTATE_REFRESH_TOKENS': env_bool('JWT_ROTATE_REFRESH_TOKENS', True),
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173',
)
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', '')

MAX_LOGIN_ATTEMPTS = env_int('MAX_LOGIN_ATTEMPTS', 3)
LOGIN_LOCKOUT_MINUTES = env_int('LOGIN_LOCKOUT_MINUTES', 30)

# Decolecta / SUNAT — consulta RUC (token solo en servidor, nunca en frontend)
APIS_NET_PE_TOKEN = os.getenv('APIS_NET_PE_TOKEN', '')
DECOLECTA_API_URL = os.getenv('DECOLECTA_API_URL', 'https://api.decolecta.com/v1')
DECOLECTA_API_TIMEOUT = env_int('DECOLECTA_API_TIMEOUT', 15)

# Órdenes de compra — serie y correlativo
ORDEN_COMPRA_SERIE_DEFAULT = os.getenv('ORDEN_COMPRA_SERIE_DEFAULT', '2026')

# MySMSGate — SMS al teléfono del usuario (Android gateway + SIM)
MYSMSGATE_ENABLED = env_bool('MYSMSGATE_ENABLED', False)
MYSMSGATE_API_KEY = os.getenv('MYSMSGATE_API_KEY', '')
MYSMSGATE_API_URL = os.getenv('MYSMSGATE_API_URL', 'https://mysmsgate.net/api/v1/send')
MYSMSGATE_DEVICE_ID = os.getenv('MYSMSGATE_DEVICE_ID', '')
MYSMSGATE_TIMEOUT = env_int('MYSMSGATE_TIMEOUT', 15)
MYSMSGATE_SMS_TODAS = env_bool('MYSMSGATE_SMS_TODAS', True)

# Seguridad HTTP (activar en producción con HTTPS)
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', False)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', False)
SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 0)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 31536000)
