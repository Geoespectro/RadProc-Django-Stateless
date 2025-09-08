# web/settings.py — STATeless ready

import os
from pathlib import Path
from django.contrib.messages import constants as messages

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------
# Seguridad / Debug
# ------------------------------------------------------------
# En producción, define SECRET_KEY y DEBUG mediante variables de entorno.
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-NO-USAR-EN-PROD')
DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() == 'true'

# Permite hosts desde env (CSV). En dev: '*'
ALLOWED_HOSTS = [h for h in os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',') if h]  # p.ej: "app.midominio.com,localhost"

# Si tu backend estará detrás de un proxy/ingress que termina TLS:
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Endurecimiento (activado si DEBUG=False)
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 60 * 60 * 24 if not DEBUG else 0  # 1 día (ajusta en prod)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Si conocés tu dominio final (https), decláralo aquí (CSV)
# Ej.: "https://app.midominio.com,https://*.midominio.com"
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o]

# ------------------------------------------------------------
# Apps
# ------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',

    # ⚠️ Mantenemos sesiones porque tu UI las usa para overrides/avisos,
    #    pero sin DB (ver SESSION_ENGINE más abajo).
    'django.contrib.sessions',

    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Tu app
    'interfaz',
]

# ------------------------------------------------------------
# Middleware
# ------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    # Mantener por compatibilidad de UI (usa mensajes y sesión en cookie)
    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ------------------------------------------------------------
# URLs / WSGI
# ------------------------------------------------------------
ROOT_URLCONF = 'web.urls'
WSGI_APPLICATION = 'web.wsgi.application'

# ------------------------------------------------------------
# Templates
# ------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Incluimos explícitamente la carpeta de templates de tu app
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

# ------------------------------------------------------------
# Base de datos (no usada por el procesamiento stateless)
# ------------------------------------------------------------
# La dejamos en sqlite para dev (admin/mensajes podrían usarla),
# pero el flujo de procesamiento NO persiste nada.
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DJANGO_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DJANGO_DB_NAME', BASE_DIR / 'db.sqlite3'),
    }
}

# ------------------------------------------------------------
# Sesiones en COOKIE (sin DB) — STATeless-friendly para tu UI
# ------------------------------------------------------------
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_AGE = int(os.getenv('DJANGO_SESSION_COOKIE_AGE', str(30 * 60)))  # 30 min
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False

# ------------------------------------------------------------
# i18n / zona horaria
# ------------------------------------------------------------
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True  # True + TZ=America/Argentina/Buenos_Aires

# ------------------------------------------------------------
# Archivos estáticos
# ------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "interfaz" / "static"]  # tu carpeta actual
STATIC_ROOT = BASE_DIR / "staticfiles"                 # para 'collectstatic' en despliegues

# ------------------------------------------------------------
# Subidas totalmente en memoria (ZIP de entrada)
# ------------------------------------------------------------
# Ajusta según el tamaño típico de tus ZIP
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE', str(200 * 1024 * 1024)))  # 200 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE', str(250 * 1024 * 1024)))  # 250 MB

# ------------------------------------------------------------
# Mensajes (tu mapeo existente)
# ------------------------------------------------------------
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# ------------------------------------------------------------
# Primary keys
# ------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
