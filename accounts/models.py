from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extends Django's built-in User model to store role, contact,
    location, and verification state for all HopeConnect users.
    """
    ROLE_CHOICES = [
        ('Donor', 'Donor'),
        ('NGO', 'NGO'),
        ('Volunteer', 'Volunteer'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='Donor'
    )
    phone = models.CharField(
        max_length=15,
        blank=True
    )
    address = models.TextField(
        blank=True
    )
    city = models.CharField(
        max_length=100,
        blank=True
    )
    profile_image = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Donors are auto-verified; NGOs and Volunteers require admin verification."
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def is_donor(self):
        return self.role == 'Donor'

    @property
    def is_ngo(self):
        return self.role == 'NGO'

    @property
    def is_volunteer(self):
        return self.role == 'Volunteer'

    @property
    def is_admin(self):
        return bool(self.user.is_staff or self.user.is_superuser)


class NGOProfile(models.Model):
    """
    Stores verification documents and organization credentials for NGOs.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='ngo_profile'
    )
    organization_name = models.CharField(
        max_length=200
    )
    registration_number = models.CharField(
        max_length=100,
        unique=True,
        help_text="Government or Trust registration number"
    )
    contact_person = models.CharField(
        max_length=100
    )
    website = models.URLField(
        blank=True,
        null=True
    )
    mission = models.TextField(
        blank=True,
        help_text="Overview of NGO cause and beneficiaries"
    )
    verification_document = models.FileField(
        upload_to='ngo_docs/',
        blank=True,
        null=True,
        help_text="Registration certificate or official letter (PDF/Image)"
    )
    is_approved = models.BooleanField(
        default=False
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_ngos'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "NGO Profile"
        verbose_name_plural = "NGO Profiles"

    def __str__(self):
        return f"{self.organization_name} (NGO: {self.user.username})"


class VolunteerProfile(models.Model):
    """
    Stores verification details, vehicle type, and availability for volunteers.
    """
    VEHICLE_CHOICES = [
        ('None/Walking', 'None / Walking'),
        ('Bicycle', 'Bicycle'),
        ('Motorcycle/Scooter', 'Motorcycle / Scooter'),
        ('Car', 'Car'),
        ('Van/Truck', 'Van / Truck'),
    ]

    AVAILABILITY_CHOICES = [
        ('Available', 'Available for Pickups'),
        ('Busy', 'Temporarily Busy'),
        ('Inactive', 'Inactive'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='volunteer_profile'
    )
    id_proof_document = models.FileField(
        upload_to='volunteer_ids/',
        blank=True,
        null=True,
        help_text="Government ID proof (Aadhaar/Driving License/Voter ID)"
    )
    vehicle_type = models.CharField(
        max_length=50,
        choices=VEHICLE_CHOICES,
        default='None/Walking'
    )
    availability_status = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default='Available'
    )
    is_approved = models.BooleanField(
        default=False
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_volunteers'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Volunteer Profile"
        verbose_name_plural = "Volunteer Profiles"

    def __str__(self):
        return f"Volunteer: {self.user.username} ({self.vehicle_type})"