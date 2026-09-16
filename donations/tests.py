from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, time, timedelta

from accounts.models import UserProfile, NGOProfile
from donations.models import DonationCategory, Donation, Category
from donations.forms import DonationForm


class DonationsModelAndViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.donor = User.objects.create_user(
            username='donor_test',
            password='password123'
        )
        UserProfile.objects.create(user=self.donor, role='DONOR', is_verified=True, city='Kochi')

        self.category = DonationCategory.objects.create(
            name='Cooked Food & Meals',
            description='Surplus food'
        )
        self.other_category = DonationCategory.objects.create(
            name='Blankets',
            description='Winter bedding'
        )

        # Verified NGO
        self.verified_ngo = User.objects.create_user(
            username='verified_ngo',
            password='password123'
        )
        UserProfile.objects.create(user=self.verified_ngo, role='NGO', is_verified=True, city='Kochi')
        NGOProfile.objects.create(
            user=self.verified_ngo,
            organization_name='Verified NGO Org',
            registration_number='REG-001',
            contact_person='Manager John',
            is_approved=True
        )

        # Unverified NGO
        self.unverified_ngo = User.objects.create_user(
            username='unverified_ngo',
            password='password123'
        )
        UserProfile.objects.create(user=self.unverified_ngo, role='NGO', is_verified=False, city='Kochi')
        NGOProfile.objects.create(
            user=self.unverified_ngo,
            organization_name='Unverified NGO Org',
            registration_number='REG-002',
            contact_person='Applicant Dave',
            is_approved=False
        )

    def test_donation_form_valid(self):
        form = DonationForm(data={
            'title': 'Hot Meals',
            'category': self.category.id,
            'description': 'Delicious hot meals for 20 people',
            'quantity': '20 packs',
            'pickup_address': 'MG Road, Kochi',
            'pickup_date': '2026-10-10',
            'pickup_time': '12:00:00',
        })
        self.assertTrue(form.is_valid())

    def test_create_donation_view_donor_only(self):
        self.client.login(username='donor_test', password='password123')
        res = self.client.post(reverse('create_donation'), {
            'title': 'Warm Clothes Batch',
            'category': self.other_category.id,
            'description': 'Assorted coats and sweaters',
            'quantity': '10 bags',
            'pickup_address': 'Panampilly Nagar',
            'pickup_date': '2026-10-12',
            'pickup_time': '11:00:00',
        })
        self.assertEqual(res.status_code, 302)
        donation = Donation.objects.get(title='Warm Clothes Batch')
        self.assertEqual(donation.donor, self.donor)
        self.assertEqual(donation.status, 'AVAILABLE')
        self.client.logout()

        # Non-donor cannot post
        self.client.login(username='verified_ngo', password='password123')
        blocked_res = self.client.post(reverse('create_donation'), {
            'title': 'Illegal Post',
            'category': self.category.id,
            'quantity': '1',
            'pickup_address': 'Nowhere',
        })
        self.assertEqual(blocked_res.status_code, 302)
        self.assertFalse(Donation.objects.filter(title='Illegal Post').exists())

    def test_donation_catalog_and_filtering(self):
        d1 = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Rice Bowls',
            description='Hot rice bowls',
            quantity='30 packs',
            pickup_address='Marine Drive, Kochi',
            status='AVAILABLE'
        )
        d2 = Donation.objects.create(
            donor=self.donor,
            category=self.other_category,
            title='Warm Blankets',
            description='Winter blankets',
            quantity='15 blankets',
            pickup_address='Fort Kochi',
            status='AVAILABLE'
        )

        res = self.client.get(reverse('donations_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Rice Bowls')
        self.assertContains(res, 'Warm Blankets')

        # Filter by category
        cat_res = self.client.get(reverse('donations_list'), {'category': self.category.id})
        self.assertContains(cat_res, 'Rice Bowls')
        self.assertNotContains(cat_res, 'Warm Blankets')

        # Search by title
        search_title = self.client.get(reverse('donations_list'), {'q': 'Rice'})
        self.assertContains(search_title, 'Rice Bowls')
        self.assertNotContains(search_title, 'Warm Blankets')

        # Search by pickup_address
        search_addr = self.client.get(reverse('donations_list'), {'q': 'Fort Kochi'})
        self.assertContains(search_addr, 'Warm Blankets')
        self.assertNotContains(search_addr, 'Rice Bowls')

    def test_donation_detail_verification_notices(self):
        donation = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Fruit Crates',
            description='Fresh apples and oranges',
            quantity='5 crates',
            pickup_address='Edappally',
            status='AVAILABLE'
        )

        # Verified NGO sees Request Donation
        self.client.login(username='verified_ngo', password='password123')
        v_res = self.client.get(reverse('donation_detail', kwargs={'pk': donation.id}))
        self.assertEqual(v_res.status_code, 200)
        self.assertContains(v_res, 'Request Donation')
        self.client.logout()

        # Unverified NGO sees Admin verification required notice
        self.client.login(username='unverified_ngo', password='password123')
        uv_res = self.client.get(reverse('donation_detail', kwargs={'pk': donation.id}))
        self.assertEqual(uv_res.status_code, 200)
        self.assertContains(uv_res, 'Admin verification required to request items.')
        self.assertNotContains(uv_res, 'Request Donation')
        self.client.logout()

    def test_my_donations_view(self):
        Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Donor Item A',
            quantity='5',
            pickup_address='Vyttila',
            status='AVAILABLE'
        )
        self.client.login(username='donor_test', password='password123')
        res = self.client.get(reverse('my_donations'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Donor Item A')
