"""
Django settings for manillas project.

Generated by 'django-admin startproject' using Django 4.1.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path
import os
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-+!fz@19oq67d5_h430^m7ohtb0y$c0dlho6=h&$g!@_=dj3h#1"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# IPs Access
ALLOWED_HOSTS = ['*', 'web','82.180.132.202',]
ALLOWED_IPS = ['*']
CSRF_TRUSTED_ORIGINS = [
    'http://82.180.132.202',
    'https://82.180.132.202',  # si usas HTTPS también
    "http://app.manillasbolivia.com",
    "https://app.manillasbolivia.com",
    "http://app.uniqbo.com",
    "https://app.uniqbo.com",
    "http://82.180.132.202/"

]

# Define the ASGI application
ASGI_APPLICATION = 'manillas.asgi.application'
# Application definition

INSTALLED_APPS = [
    'registration',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dashboard",
    "qrcodes.apps.QrcodesConfig",
    "payments",
    'channels',
    'qrscan',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "manillas.urls"



TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates"
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "manillas.wsgi.application"

# Asyncronous comunication 

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('redis', 6379)],  # Local Redis instance
        },
    },
}


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "mydatabase",
        "USER": "myuser",
        "PASSWORD": "mypassword",
        "HOST": "db",
        "PORT": "5432"
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "es"

TIME_ZONE = "America/La_Paz"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static"
]

MEDIA_URL = '/media/'
MEDIA_ROOT =  os.path.join(BASE_DIR, 'media')

# Celery settings
# Redis as the message broker
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
# Enable Celery Task Serialization
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
# Timezone for Celery
CELERY_TIMEZONE = "America/La_Paz"
# Task acknowledgement settings
CELERY_ACKS_LATE = True
CELERY_TASK_TRACK_STARTED = True

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = 'dashboard:inicio'
LOGOUT_REDIRECT_URL = 'registration:login'

# SMTP Config
DEFAULT_FROM_EMAIL = 'minusmaya@zohomail.com'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.zoho.com'
EMAIL_USE_SSL = True  # Enable SSL
EMAIL_USE_TLS = False
EMAIL_PORT = 465
EMAIL_HOST_USER = 'minusmaya@zohomail.com'
EMAIL_HOST_PASSWORD = 'kUyRVUsKBJ9C'


PASSWORD_RESET_TIMEOUT = 3600
MY_SITE_DOMAIN = "https://app.manillasbolivia.com/"
MY_SITE_PROTOCOL = "https"  # Change to "http" if not using HTTPS

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Payments
STRIPE_PUBLIC_KEY = "pk_test_51QeLxw4DIjWPcBFH08xjrIaXripqa0yUNjXCQNKFMi3U3mgNxOB7lrtYnGmr2DCUIHVLEBFV23FEAaEG1EREPQnY00IGe1cNdC"
STRIPE_SECRET_KEY = "sk_test_51QeLxw4DIjWPcBFHlEVvcJrRgpRAqWkIxusUWmddpMkCcXH8ueA0GgFWqo7PPdh5F3qtWjOGRCsvu4qbFds8CtiM00hT1nb9Wb"
STRIPE_WEBHOOK_KEY = "whsec_QnBZ2csUNeEc1nrd2P3bp9Hfk1MPAKG4"


DATA_UPLOAD_MAX_NUMBER_FIELDS = 80000  # Adjust this number as needed
