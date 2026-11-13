from django.test import TestCase,Client
from .models import Product,UpdateLog
from .prices import amount,fetch_price,parse_price
from django.contrib.auth.models import User
class ShopTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user('admin',password='AdminTest!987',is_staff=True)
        self.client.force_login(self.admin)
        self.p=Product.objects.create(name='یخچال تست',brand='TEST',category='یخچال و فریزر',price=1000000,source='demo://prices')
    def test_home(self):self.assertContains(self.client.get('/'),'خانه‌نو')
    def test_list(self):self.assertEqual(len(self.client.get('/api/products/').json()['products']),1)
    def test_update(self):
        r=self.client.post('/api/update/',{'ids':[self.p.id]},content_type='application/json');self.assertTrue(r.json()['results'][0]['ok']);self.assertEqual(UpdateLog.objects.count(),1)
    def test_bad_source(self):
        self.p.source='http://127.0.0.1/';self.p.save();r=self.client.post('/api/update/',{'ids':[self.p.id]},content_type='application/json');self.assertFalse(r.json()['results'][0]['ok']);self.p.refresh_from_db();self.assertEqual(self.p.price,1000000)
    def test_currency(self):self.assertEqual(amount('۱۲۳٬۴۰۰','rial'),12340)
    def test_invalid_price(self):
        for val in ['-1','NaN','Infinity','0','1.5']:
            with self.assertRaises(ValueError):amount(val,'toman')
    def test_create(self):
        r=self.client.post('/api/products/',{'name':'جدید','brand':'LG','category':'نظافت','price':'12345','source':'demo://prices','unit':'toman'},content_type='application/json');self.assertEqual(r.status_code,200)
    def test_csrf(self):
        c=Client(enforce_csrf_checks=True);self.assertEqual(c.post('/api/update/',{'ids':[]},content_type='application/json').status_code,403)

    def test_anonymous_denied(self):
        self.client.logout()
        for path in ['/api/products/','/api/update/','/api/price-preview/']:
            self.assertEqual(self.client.post(path,{},content_type='application/json').status_code,401)
        self.assertNotIn('source',self.client.get('/api/products/').json()['products'][0])
    def test_customer_denied(self):
        u=User.objects.create_user('customer',password='UserTest!987');self.client.force_login(u)
        for path in ['/api/products/','/api/update/','/api/price-preview/']:
            self.assertEqual(self.client.post(path,{},content_type='application/json').status_code,403)
    def test_registration_cannot_grant_admin(self):
        self.client.logout()
        r=self.client.post('/api/account/',{'action':'register','username':'newbuyer','password':'SafeExample!5721','is_staff':True},content_type='application/json')
        self.assertEqual(r.status_code,200,r.content);self.assertFalse(r.json()['is_admin'])
        self.assertFalse(User.objects.get(username='newbuyer').is_staff)
    def test_login_logout(self):
        self.client.logout()
        r=self.client.post('/api/account/',{'action':'login','username':'admin','password':'AdminTest!987'},content_type='application/json')
        self.assertTrue(r.json()['is_admin'])
        self.client.post('/api/logout/')
        self.assertFalse(self.client.get('/api/account/').json()['authenticated'])
    def test_preview_does_not_write(self):
        r=self.client.post('/api/price-preview/',{'source':'demo://prices','unit':'toman'},content_type='application/json')
        self.assertEqual(r.status_code,200);self.p.refresh_from_db();self.assertEqual(self.p.price,1000000)
    def test_multiple_prices_rejected(self):
        with self.assertRaises(ValueError):parse_price('{"offers":[{"price":100},{"price":200}]}','application/json','','toman')
    def test_aggregate_rejected(self):
        with self.assertRaises(ValueError):parse_price('{"offers":{"@type":"AggregateOffer","lowPrice":100}}','application/json','','toman')
    def test_html_price(self):
        self.assertEqual(parse_price('<meta itemprop="price" content="123400">','text/html','','rial'),12340)

    def test_partitioned_cookie_flags(self):
        r=self.client.get('/api/account/')
        cookie=r.cookies['csrftoken']
        self.assertTrue(cookie['secure']);self.assertTrue(cookie['partitioned'])
        self.assertEqual(cookie['samesite'],'None')
        self.assertIn('no-store',r['Cache-Control'])
    def test_csrf_missing_cookie_code(self):
        c=Client(enforce_csrf_checks=True)
        r=c.post('/api/account/',{},content_type='application/json')
        self.assertEqual(r.status_code,403)
        self.assertEqual(r.json()['code'],'csrf_cookie_missing')
    def test_csrf_untrusted_origin_rejected(self):
        c=Client(enforce_csrf_checks=True)
        token=c.get('/api/account/').json()['csrf']
        r=c.post('/api/account/',{},content_type='application/json',HTTP_X_CSRFTOKEN=token,HTTP_ORIGIN='https://evil.invalid')
        self.assertEqual(r.status_code,403)
        self.assertEqual(r.json()['code'],'csrf_origin_rejected')


class PreviewAuthTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user('previewadmin',password='AdminTest!987',is_staff=True)
        self.customer=User.objects.create_user('previewcustomer',password='UserTest!987')
        self.c=Client(enforce_csrf_checks=True)
    def boot(self):
        token=self.c.get('/api/preview-session/').json()['preview_token'];self.c.cookies.clear();return token
    def post(self,path,token,data):
        self.c.cookies.clear()
        return self.c.post(path,data,content_type='application/json',HTTP_X_PREVIEW_TOKEN=token)
    def test_cookieless_login_rotation_and_logout(self):
        old=self.boot()
        r=self.post('/api/account/',old,{'action':'login','username':'previewadmin','password':'AdminTest!987'})
        self.assertEqual(r.status_code,200);self.assertTrue(r.json()['is_admin'])
        token=r.json()['preview_token'];self.assertNotEqual(old,token)
        self.assertEqual(self.post('/api/update/',old,{'ids':[]}).status_code,401)
        self.assertEqual(self.post('/api/update/',token,{'ids':[]}).status_code,200)
        self.assertEqual(self.post('/api/logout/',token,{}).status_code,200)
        self.assertEqual(self.post('/api/update/',token,{'ids':[]}).status_code,401)
    def test_cookieless_customer_cannot_manage(self):
        r=self.post('/api/account/',self.boot(),{'action':'login','username':'previewcustomer','password':'UserTest!987'})
        self.assertFalse(r.json()['is_admin'])
        self.assertEqual(self.post('/api/update/',r.json()['preview_token'],{'ids':[]}).status_code,403)
    def test_invalid_token_and_wrong_password(self):
        self.assertEqual(self.post('/api/account/','x'*43,{}).status_code,401)
        r=self.post('/api/account/',self.boot(),{'action':'login','username':'previewadmin','password':'wrong'})
        self.assertEqual(r.status_code,400)
    def test_cookie_admin_not_inherited_by_anonymous_token(self):
        token=self.boot();self.c.force_login(self.admin)
        r=self.c.post('/api/update/',{'ids':[]},content_type='application/json',HTTP_X_PREVIEW_TOKEN=token)
        self.assertEqual(r.status_code,401)
    def test_expired_preview_token(self):
        from .models import PreviewSession
        from django.utils import timezone
        from datetime import timedelta
        token=self.boot();PreviewSession.objects.update(expires=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.post('/api/update/',token,{'ids':[]}).status_code,401)


class SourceDiagnosticsTests(TestCase):
    def test_unicode_and_html_url(self):
        from .prices import normalize_url
        url=normalize_url(' https://example.com/یخچال/?utm_medium=PPC&amp;utm_source=Torob ')
        self.assertIn('%DB%8C',url);self.assertNotIn('&amp;',url);self.assertIn('&utm_source=',url)
    def test_timeout_is_identified(self):
        from .prices import network_error
        import urllib3
        err=network_error(urllib3.exceptions.ReadTimeoutError(None,'/','timeout'))
        self.assertEqual(err.code,'source_timeout')
    def test_timeout_does_not_change_saved_price(self):
        from unittest.mock import patch
        from .prices import PriceSourceError
        admin=User.objects.create_user('diagnosticsadmin',is_staff=True)
        self.client.force_login(admin)
        p=Product.objects.create(name='test',brand='test',category='نظافت',price=1234,source='https://example.com/')
        with patch('shop.views.fetch_price',side_effect=PriceSourceError('source_timeout','مهلت اتصال تمام شد')):
            r=self.client.post('/api/price-preview/',{'source':p.source,'unit':'toman'},content_type='application/json')
            self.assertEqual(r.json()['code'],'source_timeout')
            r=self.client.post('/api/update/',{'ids':[p.id]},content_type='application/json')
            self.assertFalse(r.json()['results'][0]['ok'])
        p.refresh_from_db();self.assertEqual(p.price,1234)
