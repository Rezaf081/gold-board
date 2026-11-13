"""Pure price extraction: never executes HTML/scripts or downloads page resources."""
import json,csv,io,re
from decimal import Decimal,InvalidOperation
from bs4 import BeautifulSoup

class ExtractionError(ValueError):pass

def currency(value):
    s=str(value or '').strip().lower()
    if s in ('irr','rial','ریال'):return 'rial'
    if s in ('irt','toman','تومان','تومن'):return 'toman'
    if s:return 'unsupported'
    return None

def number(value):
    s=str(value).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789'))
    s=re.sub(r'[\s\u200c\u200e\u200f\u202a-\u202e]','',s).replace('٬',',')
    # Some Persian sites display U+066B between three-digit groups.
    if re.fullmatch(r'\d{1,3}(?:٫\d{3})+',s):s=s.replace('٫','')
    else:s=s.replace('٫','.')
    s=s.replace(',','')
    try:n=Decimal(s)
    except InvalidOperation:raise ExtractionError('عدد قیمت معتبر نیست.')
    if not n.is_finite() or n<=0 or n>10**13:raise ExtractionError('قیمت باید مثبت و در محدوده مجاز باشد.')
    return n

def extract(text,content='text/html',path='',unit='toman'):
    if unit not in ('auto','toman','rial'):raise ExtractionError('واحد منبع معتبر نیست.')
    candidates=[];title='';warnings=[]
    def add(value,detected,method):
        detected=currency(detected)
        if detected=='unsupported':raise ExtractionError('واحد پول منبع پشتیبانی نمی‌شود؛ فقط ریال و تومان مجاز است.')
        resolved=detected or (unit if unit!='auto' else None)
        if not resolved:raise ExtractionError('واحد پول در منبع مشخص نیست؛ ریال یا تومان را دستی انتخاب کنید.')
        if detected and unit!='auto' and detected!=unit:warnings.append('واحد اعلام‌شده در خود منبع مبنا قرار گرفت؛ با انتخاب دستی شما متفاوت است.')
        if not detected:warnings.append('واحد پول در داده مشخص نبود؛ انتخاب دستی شما استفاده شد.')
        n=number(value)/(10 if resolved=='rial' else 1)
        if n!=n.to_integral_value() or n>10**12:raise ExtractionError('قیمت به تومان صحیح تبدیل نمی‌شود یا خارج از محدوده است.')
        candidates.append({'price':int(n),'original_price':str(value),'source_unit':resolved,'method':method})
    def offers(obj,inherited=None):
        if isinstance(obj,list):
            for x in obj:offers(x,inherited)
        elif isinstance(obj,dict):
            cur=obj.get('priceCurrency',inherited)
            if obj.get('@type')=='AggregateOffer' or 'lowPrice' in obj or 'highPrice' in obj:raise ExtractionError('منبع بازه قیمت یا چند فروشنده دارد؛ انتخاب خودکار کمترین قیمت فعال نیست.')
            if str(obj.get('availability','')).split('/')[-1] in ('OutOfStock','Discontinued','SoldOut'):raise ExtractionError('منبع این محصول را ناموجود یا غیرقابل سفارش اعلام کرده؛ قیمت اعمال نشد.')
            if 'price' in obj:add(obj['price'],cur,'JSON / JSON-LD')
            elif 'offers' in obj:offers(obj['offers'],cur)
            elif 'priceSpecification' in obj:offers(obj['priceSpecification'],cur)
    def structured(docs,plain=False):
        nonlocal title
        nodes=[]
        def collect(x):
            if isinstance(x,list):
                for y in x:collect(y)
            elif isinstance(x,dict):
                nodes.append(x)
                for key in ('@graph','mainEntity'):collect(x.get(key))
        for d in docs:collect(d)
        products=[n for n in nodes if 'Product' in (n.get('@type') if isinstance(n.get('@type'),list) else [n.get('@type')])]
        if len(products)>1:raise ExtractionError('چند محصول در داده ساختاریافته وجود دارد؛ صفحه یک محصول لازم است.')
        if products:
            title=str(products[0].get('name',''));offers(products[0])
        elif plain:
            for n in nodes:
                if any(k in n for k in ('price','offers','lowPrice')):offers(n)
    if 'json' in content or text.lstrip().startswith(('{','[')):
        try:structured([json.loads(text)],plain=True)
        except json.JSONDecodeError:raise ExtractionError('ساختار فایل JSON معتبر نیست.')
    elif 'csv' in content or path.lower().endswith('.csv'):
        rows=list(csv.DictReader(io.StringIO(text.lstrip('\ufeff'))))
        if len(rows)!=1 or not rows[0].get('price'):raise ExtractionError('CSV باید یک ردیف محصول با ستون price داشته باشد.')
        title=rows[0].get('name','');add(rows[0]['price'],rows[0].get('currency'),'CSV')
    else:
        soup=BeautifulSoup(text,'html.parser')
        heading=soup.select_one('h1.product_title, h1');title=heading.get_text(' ',strip=True) if heading else ''
        docs=[]
        for tag in soup.select('script[type="application/ld+json"]'):
            try:docs.append(json.loads(tag.get_text()))
            except json.JSONDecodeError:continue
        structured(docs)
        # Only inspect primary purchase/summary price; never scan all page numbers.
        if not candidates:
            scopes=soup.select('.summary .price, .entry-summary .price, [data-product-price]')
            for scope in scopes:
                if scope.find_parent(class_=re.compile(r'^(related|upsells|cross-sells)$')):continue
                selected=scope.select('ins .amount, ins bdi') or scope.select('.amount') or [scope]
                for node in selected:
                    if node.find_parent('del'):continue
                    copy=BeautifulSoup(str(node),'html.parser')
                    for el in copy.select('del,script,style'):el.decompose()
                    raw=copy.get_text(' ',strip=True)
                    detected='toman' if re.search('تومان|تومن',raw) else 'rial' if 'ریال' in raw else None
                    clean=re.sub('تومان|تومن|ریال','',raw).strip()
                    if re.fullmatch(r'[\d۰-۹٠-٩\s,٬٫.\u200c\u200e\u200f]+',clean):add(clean,detected,'بخش قیمت اصلی محصول (HTML)')
            if not candidates:
                root=soup.select_one('.summary,.entry-summary') or soup
                tags=root.select('[itemprop="price"],meta[property="product:price:amount"]')
                for tag in tags:
                    if tag.find_parent('del') or tag.find_parent(class_=re.compile(r'^(related|upsells|cross-sells)$')):continue
                    cur=soup.select_one('[itemprop="priceCurrency"],meta[property="product:price:currency"]')
                    add(tag.get('content') or tag.get_text(strip=True),cur.get('content') if cur else None,'متادیتای قیمت HTML')
    if not candidates:raise ExtractionError('قیمت قابل تشخیص پیدا نشد؛ HTML باید شامل قیمت واقعی محصول باشد. صفحات جاوااسکریپتی یا قالب اختصاصی نیاز به بررسی دارند.')
    values={c['price'] for c in candidates}
    if len(values)!=1:raise ExtractionError('چند قیمت متفاوت پیدا شد؛ برای جلوگیری از خطا هیچ قیمتی انتخاب نشد.')
    return {**candidates[0],'title':title[:300],'warnings':list(dict.fromkeys(warnings)),'candidate_count':len(candidates)}
