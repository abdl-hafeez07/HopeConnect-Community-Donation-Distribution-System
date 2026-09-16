from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from accounts.models import UserProfile, NGOProfile
from donations.models import DonationCategory, Donation
from donation_requests.models import DonationRequest


class DashboardViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Donor User
        self.donor = User.objects.create_user(username='dash_donor', password='password123')
        UserProfile.objects.create(user=self.donor, role='DONOR', is_verified=True, city='Kochi')

        # Other Donor User
        self.other_donor = User.objects.create_user(username='other_donor', password='password123')
        UserProfile.objects.create(user=self.other_donor, role='DONOR', is_verified=True, city='Kochi')

        # Verified NGO User
        self.verified_ngo = User.objects.create_user(username='dash_ngo_v', password='password123')
        UserProfile.objects.create(user=self.verified_ngo, role='NGO', is_verified=True, city='Kochi')
        NGOProfile.objects.create(
            user=self.verified_ngo,
            organization_name='Verified NGO',
            registration_number='V-123',
            is_approved=True
        )

        # Unverified NGO User
        self.unverified_ngo = User.objects.create_user(username='dash_ngo_uv', password='password123')
        UserProfile.objects.create(user=self.unverified_ngo, role='NGO', is_verified=False, city='Kochi')
        NGOProfile.objects.create(
            user=self.unverified_ngo,
            organization_name='Pending NGO',
            registration_number='P-456',
            is_approved=False
        )

        # Category
        self.category = DonationCategory.objects.create(name='Food Packs', description='Meals')

    def test_donor_dashboard_metrics_and_permissions(self):
        # 1. Non-donor cannot access donor dashboard
        self.client.login(username='dash_ngo_v', password='password123')
        forbidden_res = self.client.get(reverse('dashboard:donor_dashboard'))
        self.assertEqual(forbidden_res.status_code, 302)
        self.client.logout()

        # 2. Donor creates donations in various statuses
        d_avail = Donation.objects.create(
            donor=self.donor, category=self.category, title='Avail 1',
            quantity='10', pickup_address='Kochi', status='AVAILABLE'
        )
        d_req = Donation.objects.create(
            donor=self.donor, category=self.category, title='Req 1',
            quantity='10', pickup_address='Kochi', status='REQUESTED'
        )
        d_app = Donation.objects.create(
            donor=self.donor, category=self.category, title='App 1',
            quantity='10', pickup_address='Kochi', status='APPROVED'
        )
        d_comp = Donation.objects.create(
            donor=self.donor, category=self.category, title='Comp 1',
            quantity='10', pickup_address='Kochi', status='COMPLETED'
        )

        # Pending request on d_req
        req_pending = DonationRequest.objects.create(
            donation=d_req, ngo=self.verified_ngo, message='Need for soup kitchen', status='PENDING'
        )

        self.client.login(username='dash_donor', password='password123')
        res = self.client.get(reverse('dashboard:donor_dashboard'))
        self.assertEqual(res.status_code, 200)

        # Check metric context
        self.assertEqual(res.context['total_donations'], 4)
        self.assertEqual(res.context['available_count'], 1)
        self.assertEqual(res.context['pending_requests_count'], 1)
        self.assertEqual(res.context['approved_count'], 1)
        self.assertEqual(res.context['completed_count'], 1)

        # Check active requests list
        self.assertEqual(len(res.context['active_requests']), 1)
        self.assertEqual(res.context['active_requests'][0], req_pending)

        # Check HTML contains inline action buttons and donation info
        self.assertContains(res, 'Avail 1')
        self.assertContains(res, 'Approve')
        self.assertContains(res, 'Reject')

    def test_ngo_dashboard_metrics_and_verification_banner(self):
        # 1. Non-NGO cannot access ngo dashboard
        self.client.login(username='dash_donor', password='password123')
        forbidden_res = self.client.get(reverse('dashboard:ngo_dashboard'))
        self.assertEqual(forbidden_res.status_code, 302)
        self.client.logout()

        # 2. System donations
        d1 = Donation.objects.create(
            donor=self.donor, category=self.category, title='System Avail 1',
            quantity='5', pickup_address='Marine Drive', status='AVAILABLE'
        )
        d2 = Donation.objects.create(
            donor=self.donor, category=self.category, title='System Avail 2',
            quantity='15', pickup_address='Fort Kochi', status='AVAILABLE'
        )

        # Requests by verified NGO
        req_p = DonationRequest.objects.create(
            donation=d1, ngo=self.verified_ngo, message='Pending request', status='PENDING'
        )
        req_a = DonationRequest.objects.create(
            donation=d2, ngo=self.verified_ngo, message='Approved request', status='APPROVED'
        )
        d2.status = 'APPROVED'
        d2.save()

        # Test Verified NGO Dashboard
        self.client.login(username='dash_ngo_v', password='password123')
        res_v = self.client.get(reverse('dashboard:ngo_dashboard'))
        self.assertEqual(res_v.status_code, 200)
        self.assertTrue(res_v.context['is_verified'])
        self.assertEqual(res_v.context['available_donations_count'], 1) # only d1 is AVAILABLE
        self.assertEqual(res_v.context['my_requests_count'], 2)
        self.assertEqual(res_v.context['pending_requests_count'], 1)
        self.assertEqual(res_v.context['approved_donations_count'], 1)
        self.assertEqual(len(res_v.context['pickup_queue']), 1)
        self.assertNotContains(res_v, 'Account pending verification.')
        self.assertContains(res_v, 'Confirm Collection')
        self.client.logout()

        # Test Unverified NGO Dashboard
        self.client.login(username='dash_ngo_uv', password='password123')
        res_uv = self.client.get(reverse('dashboard:ngo_dashboard'))
        self.assertEqual(res_uv.status_code, 200)
        self.assertFalse(res_uv.context['is_verified'])
        self.assertContains(res_uv, 'Account pending verification. You can browse listings, but donation requests unlock once approved by an Admin.')
