from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=10, unique=True)
   
    def __str__(self):
        return self.user.get_full_name() or self.user.username

    class Meta:
        db_table = 'profiles'


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    platform = models.CharField(max_length=100)
    product_image = models.TextField(blank=True)
    product_url = models.URLField(max_length=1000, blank=True)
    platform_logo = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=50, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.product_name} - {self.platform}'

    @property
    def is_static_product_image(self):
        return not self.product_image.startswith(('http://', 'https://', '//'))

    class Meta:
        db_table = 'cart_items'
        ordering = ['-created_at']
        unique_together = ('user', 'product_name', 'platform', 'product_url')


class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=255)
    category = models.CharField(max_length=50, blank=True)
    searched_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.query

    class Meta:
        db_table = 'search_history'
        ordering = ['-searched_at']
        unique_together = ('user', 'query', 'category')
