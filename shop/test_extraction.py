from django.test import TestCase,Client
from django.contrib.auth.models import User
from .extraction import extract,ExtractionError
from .models import Product

class ExtractionTests(TestCase):
    def test_woocommerce_sale_ignores_related(self):
        text='<h1>یخچال تست</h1><div class="summary"><p class="price"><del><span class="amount">۲۰٬۰۰۰ تومان</span></del><ins><span class="amount">۱۵٬۰۰۰ تومان</span></ins></p></div><section class="related"><p class="price">۹۹ تومان</p></section>'
        d=extract(text,unit='auto');self.assertEqual(d['price'],15000);self.assertEqual(d['title'],'یخچال تست')
    def test_jsonld_irr_graph(self):
        text='<script type="application/ld+json">{"@graph":[{"@type":"Organization","name":"shop"},{"@type":"Product","name":"test","offers":{"@type":"Offer","price":670000000,"priceCurrency":"IRR","availability":"https://schema.org/InStock"}}]}</script>'
        d=extract(text,unit='auto');self.assertEqual(d['price'],67000000);self.assertEqual(d['source_unit'],'rial')
    def test_unsupported_currency(self):
        with self.assertRaises(ExtractionError):extract('{"price":100,"priceCurrency":"USD"}','application/json',unit='toman')
    def test_unknown_unit_needs_choice(self):
        with self.assertRaises(ExtractionError):extract('{"price":100}','application/json',unit='auto')
        self.assertEqual(extract('{"price":100}','application/json',unit='rial')['price'],10)
    def test_out_of_stock(self):
        with self.assertRaises(ExtractionError):extract('{"price":100,"availability":"https://schema.org/OutOfStock"}','application/json',unit='toman')
    def test_range_rejected(self):
        with self.assertRaises(ExtractionError):extract('{"offers":{"@type":"AggregateOffer","lowPrice":10,"highPrice":100}}','application/json')
    def test_multiple_products_rejected_even_same_price(self):
        with self.assertRaises(ExtractionError):extract('[{"@type":"Product","offers":{"price":100}},{"@type":"Product","offers":{"price":100}}]','application/json')
    def test_no_guess_from_description(self):
        with self.assertRaises(ExtractionError):extract('<h1>یخچال ۲۷ فوت</h1><p>تلفن ۰۹۱۲۳۴۵۶۷۸۹</p><p>قیمت قبلی ۵۰۰ تومان</p>',unit='auto')
    def test_persian_decimal_grouping(self):
        self.assertEqual(extract('<div class="summary"><p class="price"><span class="amount">۶۷٫۰۰۰٫۰۰۰ تومان</span></p></div>',unit='auto')['price'],67000000)
    def test_csv_currency(self):
        self.assertEqual(extract('name,price,currency\nTest,123400,IRR','text/csv',unit='auto')['price'],12340)
    def test_declared_unit_beats_manual_with_warning(self):
        d=extract('{"price":1000,"priceCurrency":"IRR"}','application/json',unit='toman')
        self.assertEqual(d['price'],100);self.assertTrue(d['warnings'])

class FileEndpointTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user('extractadmin',is_staff=True)
        self.product=Product.objects.create(name='Original',brand='test',category='نظافت',price=900)
        self.payload={'text':'{"price":12340,"priceCurrency":"IRT"}','filename':'sample.json','unit':'auto'}
    def test_permissions(self):
        self.assertEqual(self.client.post('/api/extract-file/',self.payload,content_type='application/json').status_code,401)
        user=User.objects.create_user('regular');self.client.force_login(user)
        self.assertEqual(self.client.post('/api/extract-file/',self.payload,content_type='application/json').status_code,403)
    def test_preview_never_writes(self):
        self.client.force_login(self.admin)
        r=self.client.post('/api/extract-file/',self.payload,content_type='application/json')
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['price'],12340)
        self.product.refresh_from_db();self.assertEqual(self.product.price,900)
    def test_large_file_rejected(self):
        self.client.force_login(self.admin);self.payload['text']='a'*1000001
        self.assertEqual(self.client.post('/api/extract-file/',self.payload,content_type='application/json').status_code,400)
    def test_cookieless_token_supported(self):
        from .preview_auth import issue
        token,_=issue(self.admin)
        c=Client(enforce_csrf_checks=True)
        r=c.post('/api/extract-file/',self.payload,content_type='application/json',HTTP_X_PREVIEW_TOKEN=token)
        self.assertEqual(r.status_code,200)
