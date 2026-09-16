from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile, NGOProfile
from donations.models import Category, Donation
from donation_requests.models import DonationRequest


class CompleteWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Donor
        self.donor = User.objects.create_user(username='donor_alice', password='password123')
        UserProfile.objects.create(user=self.donor, role='Donor', is_verified=True, city='Kochi')

        # 2. NGO (Verified)
        self.ngo = User.objects.create_user(username='ngo_care', password='password123')
        UserProfile.objects.create(user=self.ngo, role='NGO', is_verified=True, city='Kochi')
        NGOProfile.objects.create(
            user=self.ngo,
            organization_name='Care India Foundation',
            registration_number='REG-777',
            contact_person='Brother Joseph',
            is_approved=True
        )

        # Category
        self.category = Category.objects.create(name='Winter Blankets', description='Warm bedding')

    def test_complete_end_to_end_workflow(self):
        # Step 1: Donor logs in and creates a donation
        self.client.login(username='donor_alice', password='password123')
        create_res = self.client.post(reverse('create_donation'), {
            'title': '20 Warm Fleece Blankets',
            'category': self.category.id,
            'quantity': '20 pieces',
            'description': 'Brand new packed blankets',
            'pickup_address': '45 Fort Kochi',
            'city': 'Kochi',
        })
        self.assertEqual(create_res.status_code, 302)
        donation = Donation.objects.get(title='20 Warm Fleece Blankets')
        self.assertEqual(donation.status, Donation.STATUS_AVAILABLE)
        self.client.logout()

        # Step 2: NGO logs in and requests the donation
        self.client.login(username='ngo_care', password='password123')
        request_res = self.client.post(reverse('request_donation', kwargs={'donation_id': donation.id}), {
            'beneficiaries_count': 25,
            'message': 'We will distribute to 25 destitute elders.'
        })
        self.assertEqual(request_res.status_code, 302)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_REQUESTED)
        request_obj = DonationRequest.objects.get(donation=donation, ngo=self.ngo)
        self.assertEqual(request_obj.status, DonationRequest.STATUS_PENDING)
        self.client.logout()

        # Step 3: Donor logs in and approves the request
        self.client.login(username='donor_alice', password='password123')
        approve_res = self.client.post(
            reverse('approve_request', kwargs={'request_id': request_obj.id}),
            {'donor_notes': 'Happy to support your community foundation!'}
        )
        self.assertEqual(approve_res.status_code, 302)
        donation.refresh_from_db()
        request_obj.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_APPROVED)
        self.assertEqual(request_obj.status, DonationRequest.STATUS_APPROVED)
        self.client.logout()

        # Step 4: NGO logs in and confirms receipt of the donation
        self.client.login(username='ngo_care', password='password123')
        confirm_res = self.client.post(
            reverse('confirm_receipt', kwargs={'request_id': request_obj.id}),
            {'receipt_notes': 'All 20 blankets received in perfect condition.'}
        )
        self.assertEqual(confirm_res.status_code, 302)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_COMPLETED)
