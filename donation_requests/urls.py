from django.urls import path
from . import views

urlpatterns = [
    path('request/<int:donation_id>/', views.request_donation, name='request_donation'),
    path('review/<int:donation_id>/', views.donor_review_requests, name='review_requests'),
    path('approve/<int:request_id>/', views.approve_request, name='approve_request'),
    path('reject/<int:request_id>/', views.reject_request, name='reject_request'),
    path('confirm-receipt/<int:request_id>/', views.confirm_receipt, name='confirm_receipt'),
]
