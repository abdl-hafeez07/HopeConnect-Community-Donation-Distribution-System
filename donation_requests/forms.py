from django import forms
from .models import DonationRequest, DeliveryAssignment


class DonationRequestForm(forms.ModelForm):
    class Meta:
        model = DonationRequest
        fields = ['beneficiaries_count', 'message']
        widgets = {
            'beneficiaries_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Explain how your organization will distribute these items, target beneficiaries, and any special logistics capability...'
            }),
        }


class DeliveryUpdateForm(forms.ModelForm):
    scheduled_pickup_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Scheduled Pickup Time"
    )

    class Meta:
        model = DeliveryAssignment
        fields = [
            'status',
            'scheduled_pickup_time',
            'delivery_proof_image',
            'recipient_confirmation_name',
            'delivery_notes',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'delivery_proof_image': forms.FileInput(attrs={'class': 'form-control'}),
            'recipient_confirmation_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name of NGO representative receiving items'}),
            'delivery_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Condition upon arrival, hand-off notes, etc.'}),
        }
