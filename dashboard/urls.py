from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('donor/', views.donor_dashboard, name='donor_dashboard'),
    path('ngo/', views.ngo_dashboard, name='ngo_dashboard'),
    path('volunteer/', views.volunteer_dashboard, name='volunteer_dashboard'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('verify-ngo/<int:pk>/<str:action>/', views.verify_ngo_action, name='verify_ngo_action'),
    path('verify-volunteer/<int:pk>/<str:action>/', views.verify_volunteer_action, name='verify_volunteer_action'),
]
