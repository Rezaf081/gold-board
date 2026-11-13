"""CHIPS cookies for the HTTPS embedded preview; normal Django CSRF remains enabled."""
from http.cookies import Morsel
from django.conf import settings

# Python versions before native CHIPS support need the standard attribute registered.
Morsel._reserved.setdefault('partitioned', 'Partitioned')
Morsel._flags.add('partitioned')

class PartitionedPreviewCookiesMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        if settings.PREVIEW_PARTITIONED_COOKIES:
            for name in (settings.CSRF_COOKIE_NAME,settings.SESSION_COOKIE_NAME):
                if name in response.cookies:
                    cookie=response.cookies[name]
                    cookie['secure']=True
                    cookie['samesite']='None'
                    cookie['partitioned']=True
        if request.path.startswith('/api/') or request.path in ('/','/login/','/admin-login/'):
            response['Cache-Control']='no-store, private'
        return response
