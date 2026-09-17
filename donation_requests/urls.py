from django.urls import path
from . import views

urlpatterns = [
    # Explicit operational workflow endpoints
    path('submit/<int:donation_id>/', views.submit_request, name='submit_request'),
    path('manage/<int:request_id>/<str:action>/', views.manage_request, name='manage_request'),
    path('collect/<int:request_id>/', views.mark_collected, name='mark_collected'),
    path('complete/<int:request_id>/', views.mark_completed, name='mark_completed'),

    # Contextual review and backward-compatible aliases
    path('review/<int:donation_id>/', views.donor_review_requests, name='review_requests'),
    path('request/<int:donation_id>/', views.submit_request, name='request_donation'),
    path('accept/<int:donation_id>/', views.accept_request, name='accept_request'),
    path('request/<int:donation_id>/accept/', views.accept_request, name='accept_donation'),
    path('requests/accept/<int:request_id>/', views.accept_request, name='accept_request_by_id'),
    path('approve/<int:request_id>/', views.approve_request, name='approve_request'),
    path('reject/<int:request_id>/', views.reject_request, name='reject_request'),
    path('confirm-receipt/<int:request_id>/', views.mark_completed, name='confirm_receipt'),
]
