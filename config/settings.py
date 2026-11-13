from pathlib import Path
import os
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY','demo-only-homeware-key-change-in-production')
DEBUG=os.environ.get('DJANGO_DEBUG','1')=='1'
ALLOWED_HOSTS=['*']
INSTALLED_APPS=['django.contrib.contenttypes','django.contrib.auth','django.contrib.sessions','django.contrib.staticfiles','shop']
MIDDLEWARE=['shop.middleware.PartitionedPreviewCookiesMiddleware','django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','shop.preview_auth.PreviewAuthenticationMiddleware','shop.preview_auth.PreviewAwareCsrfMiddleware']
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.template.context_processors.csrf']}}]
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
LANGUAGE_CODE='fa-ir'
TIME_ZONE='Asia/Tehran'
USE_TZ=True
STATIC_URL='static/'
STATICFILES_DIRS=[BASE_DIR/'static']
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
CSRF_TRUSTED_ORIGINS=['https://*.e2b.app']
SESSION_COOKIE_SAMESITE='Lax'

ROOT_URLCONF='config.urls'
WSGI_APPLICATION='config.wsgi.application'

AUTH_PASSWORD_VALIDATORS=[
 {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
 {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':10}},
 {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
 {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
SESSION_COOKIE_HTTPONLY=True
# Live preview is HTTPS and may be embedded cross-site.
# For local HTTP development: PREVIEW_HTTPS=0 python manage.py runserver
if os.environ.get('PREVIEW_HTTPS','1') == '1':
    SESSION_COOKIE_SAMESITE='None'
    SESSION_COOKIE_SECURE=True
    CSRF_COOKIE_SAMESITE='None'
    CSRF_COOKIE_SECURE=True

PREVIEW_PARTITIONED_COOKIES=os.environ.get('PREVIEW_HTTPS','1')=='1'
CSRF_FAILURE_VIEW='shop.security.csrf_failure'
