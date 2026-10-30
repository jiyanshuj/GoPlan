from django.urls import path
from . import views

urlpatterns = [
    path('', views.trip_view, name='trip_view'),
    path('home/', views.trip_view, name='home'),
    path('booking/', views.final, name='booking'),
    path('forming/', views.payment, name='forming'),
    path('pay/', views.pay, name='pay'),
    path('success/', views.booking_success, name='booking_success'),
]
