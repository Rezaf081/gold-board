from django.urls import path
from shop import views,auth_views,preview_auth
urlpatterns=[path('api/extract-file/',views.extract_file),path('api/preview-session/',preview_auth.bootstrap),path('login/',views.index),path('admin-login/',views.index),path('api/account/',auth_views.account),path('api/logout/',auth_views.signout),path('api/price-preview/',views.preview_price),path('',views.index),path('api/products/',views.products),path('api/update/',views.update)]
