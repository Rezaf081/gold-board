import logging
from django.http import JsonResponse
logger=logging.getLogger('django.security.csrf')
def csrf_failure(request,reason=''):
    code='csrf_cookie_missing' if 'cookie not set' in reason else 'csrf_origin_rejected' if ('Origin checking' in reason or 'Referer checking' in reason) else 'csrf_token_invalid'
    messages={
      'csrf_cookie_missing':'مرورگر کوکی امنیتی را ارسال نکرد. ورود را در تب مستقل باز کنید؛ نیازی به خاموش‌کردن امنیت مرورگر نیست.',
      'csrf_origin_rejected':'مبدأ درخواست با تنظیمات امنیتی سایت مطابقت ندارد.',
      'csrf_token_invalid':'توکن امنیتی منقضی یا تغییر کرده است؛ دوباره تلاش کنید.',
    }
    return JsonResponse({'error':messages[code],'code':code},status=403)
