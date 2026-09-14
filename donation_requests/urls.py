from django.urls import path
from . import views

urlpatterns = [
    path('request/<int:donation_id>/', views.request_donation, name='request_donation'),
    path('review/<int:donation_id>/', views.donor_review_requests, name='review_requests'),
    path('approve/<int:request_id>/', views.approve_request, name='approve_request'),
    path('reject/<int:request_id>/', views.reject_request, name='reject_request'),
    path('volunteer/pickups/', views.available_pickups, name='available_pickups'),
    path('volunteer/claim/<int:assignment_id>/', views.claim_pickup, name='claim_pickup'),
    path('delivery/<int:assignment_id>/update/', views.update_delivery, name='update_delivery'),
    path('delivery/<int:assignment_id>/confirm-receipt/', views.confirm_receipt, name='confirm_receipt'),
]
