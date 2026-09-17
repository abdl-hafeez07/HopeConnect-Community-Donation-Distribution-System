from django import forms
from .models import Donation, DonationCategory, Category


class DonationForm(forms.ModelForm):
    pickup_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Pickup Date"
    )
    pickup_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Pickup Time"
    )
    expiry_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Expiry Date / Best Before"
    )
    delivery_option = forms.ChoiceField(
        choices=Donation.DELIVERY_CHOICES,
        required=False,
        initial='NGO_PICKUP',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Delivery & Transfer Method"
    )
    dropoff_location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. NGO Center / Community Partner Hub / Local Reading Room Desk'
        }),
        label="Drop-off Location / Community Hub"
    )

    def clean_delivery_option(self):
        return self.cleaned_data.get('delivery_option') or 'NGO_PICKUP'

    class Meta:
        model = Donation
        fields = [
            'title',
            'category',
            'description',
            'quantity',
            'delivery_option',
            'dropoff_location',
            'pickup_address',
            'pickup_date',
            'pickup_time',
            'expiry_date',
            'image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 50 Fresh Meal Packets / 10 Warm Blankets'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_category_select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the items, condition, packaging, and any handling instructions...'
            }),
            'quantity': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 50 boxes, 15 kg, 3 cartons'
            }),
            'pickup_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Full street address for pickup'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }


# Alias for backward compatibility
DonationCreateForm = DonationForm
