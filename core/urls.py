from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
]
