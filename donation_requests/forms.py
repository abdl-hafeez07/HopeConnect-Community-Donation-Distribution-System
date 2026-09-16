from django import forms
from .models import DonationRequest


class DonationRequestForm(forms.ModelForm):
    class Meta:
        model = DonationRequest
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Explain how your organization will distribute these items, target beneficiaries, and any special logistics capability...'
            }),
        }
        labels = {
            'message': 'Distribution Plan & Message',
        }
