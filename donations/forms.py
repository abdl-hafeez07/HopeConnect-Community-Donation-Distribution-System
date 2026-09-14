from django import forms
from django.utils import timezone
from .models import Donation, FoodDetail, Category


class DonationCreateForm(forms.ModelForm):
    preferred_pickup_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Preferred Pickup Time"
    )

    class Meta:
        model = Donation
        fields = [
            'title',
            'category',
            'quantity',
            'description',
            'pickup_address',
            'city',
            'pickup_landmark',
            'preferred_pickup_time',
            'image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 50 Fresh Meal Packets / 10 Warm Blankets'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category_select'}),
            'quantity': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 50 boxes, 15 kg, 3 cartons'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the items, condition, packaging, and any handling instructions...'}),
            'pickup_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full street address for pickup'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City or District'}),
            'pickup_landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nearby landmark or apartment name'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class FoodDetailForm(forms.ModelForm):
    preparation_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Preparation / Cooking Time"
    )
    expiry_time = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Expiry / Safe Consumption Deadline"
    )

    class Meta:
        model = FoodDetail
        fields = [
            'food_type',
            'dietary_type',
            'preparation_time',
            'expiry_time',
            'storage_instructions',
        ]
        widgets = {
            'food_type': forms.Select(attrs={'class': 'form-select'}),
            'dietary_type': forms.Select(attrs={'class': 'form-select'}),
            'storage_instructions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Keep refrigerated, Hot food, Consume within 4 hours'}),
        }

    def clean_expiry_time(self):
        expiry_time = self.cleaned_data.get('expiry_time')
        if expiry_time and expiry_time <= timezone.now():
            raise forms.ValidationError("Food expiry time must be in the future.")
        return expiry_time
