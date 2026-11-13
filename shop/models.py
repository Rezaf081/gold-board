from django.db import models
class Product(models.Model):
    name=models.CharField(max_length=160)
    brand=models.CharField(max_length=80)
    category=models.CharField(max_length=40)
    price=models.PositiveBigIntegerField()
    old_price=models.PositiveBigIntegerField(default=0)
    source=models.CharField(max_length=1000,blank=True)
    unit=models.CharField(max_length=10,default='toman')
    kind=models.CharField(max_length=30,default='fridge')
    updated=models.DateTimeField(null=True,blank=True)
class UpdateLog(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    message=models.CharField(max_length=300)
    success=models.BooleanField(default=True)
    created=models.DateTimeField(auto_now_add=True)

class PreviewSession(models.Model):
    token_hash=models.CharField(max_length=64,unique=True)
    user=models.ForeignKey('auth.User',null=True,blank=True,on_delete=models.CASCADE)
    auth_hash=models.CharField(max_length=64,blank=True)
    expires=models.DateTimeField(db_index=True)
