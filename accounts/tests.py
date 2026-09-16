from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile, NGOProfile


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

    def test_user_profile_creation(self):
        profile = UserProfile.objects.create(
            user=self.donor_user,
            role='DONOR',
            phone='9876543210',
            city='Kochi',
            is_verified=True
        )
        self.assertEqual(str(profile), "donor_test (DONOR)")
        self.assertTrue(profile.is_donor)
        self.assertFalse(profile.is_ngo)

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

    def test_register_donor_view(self):
        response = self.client.post(reverse('register'), {
            'username': 'new_donor',
            'email': 'new_donor@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'DONOR',
            'phone': '9876543219',
            'city': 'Kochi',
            'address': 'Marine Drive',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='new_donor')
        self.assertEqual(new_user.profile.role, 'DONOR')
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
        UserProfile.objects.create(user=self.donor_user, role='DONOR', is_verified=True)
        response = self.client.post(reverse('login'), {
            'username': 'donor_test',
            'password': 'password123'
        })
        self.assertRedirects(response, reverse('dashboard:donor_dashboard'))

    def test_ngo_login_redirect(self):
        UserProfile.objects.create(user=self.ngo_user, role='NGO', is_verified=True)
        response = self.client.post(reverse('login'), {
            'username': 'ngo_test',
            'password': 'password123'
        })
        self.assertRedirects(response, reverse('dashboard:ngo_dashboard'))
