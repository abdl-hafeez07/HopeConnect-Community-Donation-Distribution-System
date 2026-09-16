from django.urls import path
from . import views

urlpatterns = [
    path('', views.donation_list, name='donations_list'),
    path('browse/', views.donation_list, name='browse_donations'),
    path('create/', views.create_donation, name='create_donation'),
    path('<int:pk>/', views.donation_detail, name='donation_detail'),
    path('my-donations/', views.my_donations, name='my_donations'),
    path('<int:pk>/cancel/', views.cancel_donation, name='cancel_donation'),
]
