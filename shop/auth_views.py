import json,time
from functools import wraps
from django.contrib.auth import authenticate,login,logout,get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db import IntegrityError
from django.http import JsonResponse
from django.conf import settings
from .preview_auth import rotate
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods,require_POST

def admin_required(view):
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        if not request.user.is_authenticated:return JsonResponse({'error':'ابتدا وارد حساب خود شوید.'},status=401)
        if not request.user.is_staff:return JsonResponse({'error':'این عملیات فقط برای مدیر فروشگاه مجاز است.'},status=403)
        return view(request,*args,**kwargs)
    return wrapped

def state(request):
    u=request.user
    return JsonResponse({'authenticated':u.is_authenticated,'username':u.username if u.is_authenticated else '', 'is_admin':bool(u.is_authenticated and u.is_staff),'preview_token':getattr(request,'preview_token',None),'csrf':get_token(request),'csrf_cookie_present':bool(request.COOKIES.get(settings.CSRF_COOKIE_NAME))})

@require_http_methods(['GET','POST'])
def account(request):
    if request.method=='GET':return state(request)
    key='auth:'+request.META.get('REMOTE_ADDR','unknown')
    attempts=cache.get(key,0)
    if attempts>=20:return JsonResponse({'error':'تعداد تلاش‌ها زیاد است؛ ۱۰ دقیقه دیگر امتحان کنید.'},status=429)
    cache.set(key,attempts+1,600)
    try:
        d=json.loads(request.body)
        if not isinstance(d,dict):raise ValueError()
        username=d.get('username','');password=d.get('password','');action=d.get('action')
        if not isinstance(username,str) or not isinstance(password,str) or len(username)>150 or len(password)>256:raise ValueError()
        if action=='register':
            User=get_user_model();user=User(username=username.strip(),email=str(d.get('email',''))[:254])
            user.full_clean(exclude=['password']);validate_password(password,user)
            user.set_password(password);user.save();complete_login(request,user)
        elif action=='login':
            user=authenticate(request,username=username.strip(),password=password)
            if user is None:return JsonResponse({'error':'نام کاربری یا رمز عبور درست نیست.'},status=400)
            complete_login(request,user)
        else:raise ValueError()
        return state(request)
    except ValidationError as e:return JsonResponse({'error':' / '.join(e.messages)},status=400)
    except IntegrityError:return JsonResponse({'error':'این نام کاربری قبلاً ثبت شده است.'},status=400)
    except (ValueError,TypeError):return JsonResponse({'error':'اطلاعات حساب نامعتبر است.'},status=400)

@require_POST
def signout(request):
    if getattr(request,'preview_session',None) is not None:rotate(request)
    else:logout(request)
    return state(request)

def complete_login(request,user):
    if getattr(request,'preview_session',None) is not None:rotate(request,user)
    else:login(request,user)
