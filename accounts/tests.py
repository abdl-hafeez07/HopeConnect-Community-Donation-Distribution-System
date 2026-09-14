from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile, NGOProfile, VolunteerProfile


class AccountsModelAndViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.donor_user = User.objects.create_user(
            username='donor_test',
            password='password123',
            email='donor@test.com'
        )
        self.ngo_user = User.objects.create_user(
            username='ngo_test',
            password='password123',
            email='ngo@test.com'
        )
        self.vol_user = User.objects.create_user(
            username='vol_test',
            password='password123',
            email='vol@test.com'
        )

    def test_user_profile_creation(self):
        profile = UserProfile.objects.create(
            user=self.donor_user,
            role='Donor',
            phone='9876543210',
            city='Kochi',
            is_verified=True
        )
        self.assertEqual(str(profile), "donor_test (Donor)")
        self.assertTrue(profile.is_donor)
        self.assertFalse(profile.is_ngo)
        self.assertFalse(profile.is_volunteer)

    def test_ngo_profile_creation(self):
        profile = UserProfile.objects.create(
            user=self.ngo_user,
            role='NGO',
            phone='9876543211',
            city='Ernakulam',
            is_verified=False
        )
        ngo = NGOProfile.objects.create(
            user=self.ngo_user,
            organization_name='Hope Foundation',
            registration_number='REG-12345',
            contact_person='Sister Maria'
        )
        self.assertIn("Hope Foundation", str(ngo))
        self.assertFalse(ngo.is_approved)

    def test_volunteer_profile_creation(self):
        profile = UserProfile.objects.create(
            user=self.vol_user,
            role='Volunteer',
            phone='9876543212',
            city='Kochi',
            is_verified=False
        )
        vol = VolunteerProfile.objects.create(
            user=self.vol_user,
            vehicle_type='Motorcycle/Scooter',
            availability_status='Available'
        )
        self.assertEqual(vol.vehicle_type, 'Motorcycle/Scooter')
        self.assertFalse(vol.is_approved)

    def test_register_donor_view(self):
        response = self.client.post(reverse('register'), {
            'username': 'new_donor',
            'email': 'new_donor@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'Donor',
            'phone': '9876543219',
            'city': 'Kochi',
            'address': 'Marine Drive',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='new_donor')
        self.assertEqual(new_user.profile.role, 'Donor')
        self.assertTrue(new_user.profile.is_verified)

    def test_register_ngo_view(self):
        response = self.client.post(reverse('register'), {
            'username': 'new_ngo',
            'email': 'new_ngo@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'NGO',
            'phone': '9876543218',
            'city': 'Kochi',
            'address': 'MG Road',
            'organization_name': 'Care Shelter',
            'registration_number': 'REG-8888',
            'contact_person': 'David John',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='new_ngo')
        self.assertEqual(new_user.profile.role, 'NGO')
        self.assertFalse(new_user.profile.is_verified)
        self.assertEqual(new_user.ngo_profile.organization_name, 'Care Shelter')

    def test_login_and_dashboard_redirect(self):
        UserProfile.objects.create(user=self.donor_user, role='Donor', is_verified=True)
        login_success = self.client.login(username='donor_test', password='password123')
        self.assertTrue(login_success)

        response = self.client.get(reverse('dashboard_home'), follow=True)
        self.assertContains(response, "Donor Dashboard")
