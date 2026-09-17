from django import forms
from .models import DonationRequest


class DonationRequestForm(forms.ModelForm):
    class Meta:
        model = DonationRequest
        fields = ['message', 'contact_person', 'contact_phone', 'contact_email', 'pickup_notes']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Explain how your organization will distribute these items, target beneficiaries, and any special logistics capability...'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name of NGO representative coordinating pickup'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Direct contact phone number'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Official contact email'
            }),
            'pickup_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Optional logistics details, preferred pickup window, or vehicle arrangement...'
            }),
        }
        labels = {
            'message': 'Distribution Plan & Cause',
            'contact_person': 'Contact Person',
            'contact_phone': 'Contact Phone',
            'contact_email': 'Contact Email',
            'pickup_notes': 'Pickup / Logistics Notes',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not self.is_bound:
            ngo_profile = getattr(user, 'ngo_profile', None)
            profile = getattr(user, 'profile', None)
            if ngo_profile and ngo_profile.contact_person and not self.initial.get('contact_person'):
                self.initial['contact_person'] = ngo_profile.contact_person
            elif not self.initial.get('contact_person'):
                self.initial['contact_person'] = user.get_full_name() or user.username

            if profile and profile.phone and not self.initial.get('contact_phone'):
                self.initial['contact_phone'] = profile.phone

            if user.email and not self.initial.get('contact_email'):
                self.initial['contact_email'] = user.email

            if profile and profile.address and not self.initial.get('pickup_notes'):
                self.initial['pickup_notes'] = f"Organization Address: {profile.address}"
