import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Product, UpdateLog
from .auth_views import admin_required
from .prices import fetch_price,amount

def index(request):return render(request,'index.html')
@require_http_methods(['GET','POST'])
def products(request):
    if request.method=='GET':
        admin=request.user.is_authenticated and request.user.is_staff
        fields=['id','name','brand','category','price','old_price','kind','updated']
        if admin:fields+=['source','unit']
        return JsonResponse({'products':list(Product.objects.values(*fields)),'logs':list(UpdateLog.objects.order_by('-created').values('message','success','created','product__name')[:20]) if admin else []})
    return save_product(request)

@admin_required
def save_product(request):
    try:
        d=json.loads(request.body)
        name=str(d.get('name','')).strip();brand=str(d.get('brand','')).strip()
        if not name or len(name)>160 or not brand or len(brand)>80:raise ValueError('نام محصول و برند معتبر وارد کنید.')
        if d.get('category') not in ['یخچال و فریزر','شست‌وشو','پخت‌وپز','نظافت']:raise ValueError('دسته‌بندی معتبر نیست.')
        if d.get('unit') not in ['auto','toman','rial']:raise ValueError('واحد قیمت معتبر نیست.')
        source=str(d.get('source','')).strip()
        if len(source)>1000:raise ValueError('لینک بیش از حد طولانی است.')
        p=Product.objects.get(pk=d['id']) if d.get('id') else Product()
        for k,v in dict(name=name,brand=brand,category=d['category'],source=source,unit=d['unit'],price=amount(d['price'],'toman')).items():setattr(p,k,v)
        p.kind={'یخچال و فریزر':'fridge','شست‌وشو':'washer','پخت‌وپز':'coffee','نظافت':'vacuum'}[p.category];p.save()
        return JsonResponse({'ok':True})
    except (ValueError,KeyError,TypeError,AttributeError,Product.DoesNotExist):return JsonResponse({'error':'اطلاعات محصول ناقص یا نامعتبر است؛ قیمت را به تومان وارد کنید.'},status=400)
@require_http_methods(['POST'])
@admin_required
def update(request):
    try:
        data=json.loads(request.body);ids=data.get('ids',[])
        if not isinstance(ids,list) or len(ids)>30 or any(type(i)!=int or i<1 for i in ids):raise ValueError()
    except (ValueError,TypeError,AttributeError):return JsonResponse({'error':'درخواست نامعتبر است.'},status=400)
    result=[]
    for p in Product.objects.filter(id__in=ids):
        try:
            if not p.source:raise ValueError('برای این محصول لینک منبع تعیین نشده است.')
            price=fetch_price(p);old=p.price;p.old_price=old;p.price=price;p.updated=timezone.now();p.save()
            msg=f'قیمت از {old:,} به {price:,} تومان تغییر کرد.';ok=True
        except Exception as e:
            msg=str(e) if isinstance(e,ValueError) else 'ارتباط با منبع ناموفق بود؛ لینک و دسترسی سایت را بررسی کنید.';ok=False
        UpdateLog.objects.create(product=p,message=msg[:300],success=ok)
        result.append({'id':p.id,'ok':ok,'message':msg})
    return JsonResponse({'results':result})

@require_http_methods(['POST'])
@admin_required
def preview_price(request):
    try:
        data=json.loads(request.body)
        unit=data.get('unit','toman')
        if unit not in ('auto','toman','rial'):raise ValueError('واحد نامعتبر است.')
        p=Product(id=1,source=str(data.get('source','')).strip(),unit=unit,price=1000000)
        if not p.source or len(p.source)>1000:raise ValueError('لینک معتبر وارد کنید.')
        value=fetch_price(p,details=True)
        return JsonResponse({**value,'message':'قیمت خوانده شد؛ هنوز ذخیره نشده است. واحد منبع و مطابقت محصول را بررسی کنید.'})
    except Exception as e:
        return JsonResponse({'error':str(e) if isinstance(e,ValueError) else 'پردازش منبع ناموفق بود؛ قیمت قبلی تغییری نکرده است.','code':getattr(e,'code','source_parse_error')},status=400)

@require_http_methods(['POST'])
@admin_required
def extract_file(request):
    from .extraction import extract
    try:
        data=json.loads(request.body)
        text=data.get('text','');filename=str(data.get('filename',''))
        if not isinstance(text,str) or not text.strip() or len(text.encode('utf-8'))>1000000:raise ValueError('فایل باید متنی، غیرخالی و حداکثر یک مگابایت باشد.')
        ext=filename.lower().rsplit('.',1)[-1]
        if ext not in ('html','htm','json','csv'):raise ValueError('فقط HTML، JSON و CSV پشتیبانی می‌شود.')
        content={'html':'text/html','htm':'text/html','json':'application/json','csv':'text/csv'}[ext]
        result=extract(text,content,filename,data.get('unit','auto'))
        return JsonResponse({**result,'message':'استخراج از فایل ذخیره‌شده انجام شد؛ این دریافت زنده نیست. پس از بررسی نام و قیمت، می‌توانید آن را در فرم استفاده کنید.'})
    except (ValueError,TypeError,AttributeError) as e:return JsonResponse({'error':str(e),'code':'extraction_failed'},status=400)
