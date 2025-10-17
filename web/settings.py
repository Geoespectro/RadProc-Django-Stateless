# ======================================================
# web/settings.py — Configuración STATeless lista para Docker
# ======================================================

import os
from pathlib import Path
from django.contrib.messages import constants as messages

# ------------------------------------------------------
# Rutas base
# ------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------
# Seguridad / Debug
# ------------------------------------------------------
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-NO-USAR-EN-PROD')
DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() == 'true'

ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = False  # Se mantiene en falso por el modo sin TLS directo
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 86400  # 1 día
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# ------------------------------------------------------
# Aplicaciones
# ------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',  # Usamos cookies firmadas (sin DB)
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'interfaz',  # Tu app principal
]

# ------------------------------------------------------
# Middleware
# ------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Permite servir estáticos sin Nginx
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ------------------------------------------------------
# URL y WSGI
# ------------------------------------------------------
ROOT_URLCONF = 'web.urls'
WSGI_APPLICATION = 'web.wsgi.application'

# ------------------------------------------------------
# Templates
# ------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'interfaz' / 'templates'],
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

# ------------------------------------------------------
# Base de datos (solo para sesiones mínimas o admin)
# ------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DJANGO_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DJANGO_DB_NAME', BASE_DIR / 'db.sqlite3'),
    }
}

# ------------------------------------------------------
# Sesiones — modo STATeless (en cookies firmadas)
# ------------------------------------------------------
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_AGE = int(os.getenv('DJANGO_SESSION_COOKIE_AGE', '1800'))  # 30 min
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False

# ------------------------------------------------------
# Internacionalización
# ------------------------------------------------------
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------
# Archivos estáticos (Whitenoise + Docker)
# ------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "interfaz" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ------------------------------------------------------
# Subidas (ZIPs temporales en memoria)
# ------------------------------------------------------
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE', str(200 * 1024 * 1024)))  # 200 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE', str(250 * 1024 * 1024)))  # 250 MB

# ------------------------------------------------------
# Mensajes del sistema
# ------------------------------------------------------
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# ------------------------------------------------------
# Clave primaria por defecto
# ------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

