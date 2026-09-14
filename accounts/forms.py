from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import UserProfile, NGOProfile, VolunteerProfile


class UserRegisterForm(forms.ModelForm):
    ROLE_CHOICES = [
        ('Donor', 'Donor (I want to donate items/food)'),
        ('NGO', 'NGO / Charity (I want to request & distribute donations)'),
        ('Volunteer', 'Volunteer (I want to pick up & deliver donations)'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_role'}),
        label="Select Your Role"
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter strong password'}),
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm your password'}),
        min_length=6
    )
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210'})
    )
    city = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Kochi, Mumbai, Delhi'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Street address, landmark'})
    )

    # NGO Specific Fields
    organization_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registered Organization Name'})
    )
    registration_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Trust / Society / 80G Registration No.'})
    )
    contact_person = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Director or Representative Name'})
    )
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://yourngo.org'})
    )
    mission = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Brief mission & beneficiaries supported'})
    )
    verification_document = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    # Volunteer Specific Fields
    vehicle_type = forms.ChoiceField(
        required=False,
        choices=VolunteerProfile.VEHICLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    id_proof_document = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose username'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        role = cleaned_data.get('role')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        if role == 'NGO':
            if not cleaned_data.get('organization_name'):
                self.add_error('organization_name', "Organization name is required for NGOs.")
            if not cleaned_data.get('registration_number'):
                self.add_error('registration_number', "Registration number is required for NGOs.")
            if not cleaned_data.get('contact_person'):
                self.add_error('contact_person', "Contact person name is required for NGOs.")

        return cleaned_data


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class UserProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = UserProfile
        fields = ['phone', 'city', 'address', 'profile_image']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
