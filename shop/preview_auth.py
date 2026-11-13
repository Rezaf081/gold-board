"""Explicit-header, memory-only preview sessions. No ambient cookie authority."""
import hashlib,secrets
from datetime import timedelta
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.contrib.auth.models import AnonymousUser
from django.middleware.csrf import CsrfViewMiddleware
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.cache import cache
from .models import PreviewSession

API_PATHS={'/api/extract-file/','/api/account/','/api/logout/','/api/products/','/api/update/','/api/price-preview/'}

def issue(user=None):
    token=secrets.token_urlsafe(32)
    session=PreviewSession.objects.create(token_hash=hashlib.sha256(token.encode()).hexdigest(),user=user,auth_hash=user.get_session_auth_hash() if user else '',expires=timezone.now()+timedelta(minutes=60 if user else 10))
    return token,session

def rotate(request,user=None):
    request.preview_session.delete()
    token,request.preview_session=issue(user)
    request.preview_token=token
    request.user=user or AnonymousUser()

@require_GET
def bootstrap(request):
    key='preview-bootstrap:'+request.META.get('REMOTE_ADDR','unknown')
    n=cache.get(key,0)
    if n>=120:return JsonResponse({'error':'تعداد درخواست زیاد است؛ کمی بعد تلاش کنید.'},status=429)
    cache.set(key,n+1,600)
    PreviewSession.objects.filter(expires__lt=timezone.now()).delete()
    token,_=issue()
    return JsonResponse({'preview_token':token})

class PreviewAuthenticationMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        request.preview_session=None
        token=request.headers.get('X-Preview-Token')
        if token and request.path in API_PATHS:
            session=PreviewSession.objects.select_related('user').filter(token_hash=hashlib.sha256(token.encode()).hexdigest(),expires__gt=timezone.now()).first() if len(token)==43 else None
            if not session or (session.user and (not session.user.is_active or not constant_time_compare(session.auth_hash,session.user.get_session_auth_hash()))):
                return JsonResponse({'error':'نشست پیش‌نمایش منقضی شده؛ دوباره وارد شوید.','code':'preview_expired'},status=401)
            request.preview_session=session
            # Never inherit a cookie-authenticated identity when a preview token is supplied.
            request.user=session.user or AnonymousUser()
        return self.get_response(request)

class PreviewAwareCsrfMiddleware(CsrfViewMiddleware):
    def process_view(self,request,callback,args,kwargs):
        if getattr(request,'preview_session',None) is not None and request.path in API_PATHS:
            # CSRF cookie validation applies only to cookie-based auth. This separate
            # mode requires an unguessable explicit header, unreadable cross-origin
            # under SOP; no CORS allowance is installed. HTML forms cannot send it.
            if request.method not in ('GET','HEAD','OPTIONS') and request.content_type!='application/json':
                return JsonResponse({'error':'درخواست JSON لازم است.'},status=415)
            return None
        return super().process_view(request,callback,args,kwargs)
