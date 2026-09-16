from django import forms
from .models import DonationRequest


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
