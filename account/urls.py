from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name="signup"),
    path('login/', views.login, name="login"),
    path('logout/', views.logout, name="logout"),
    path('profile/', views.profile, name="profile"),
    path('cart/', views.cart, name="cart"),
    path('cart/add/', views.add_to_cart, name="add_to_cart"),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name="remove_cart_item"),
    path('cart/clear/', views.clear_cart, name="clear_cart"),
]
