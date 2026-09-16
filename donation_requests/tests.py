from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile, NGOProfile
from donations.models import DonationCategory, Donation
from donation_requests.models import DonationRequest


class OperationalWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Donor
        self.donor = User.objects.create_user(username='donor_alice', password='password123')
        UserProfile.objects.create(user=self.donor, role='DONOR', is_verified=True, city='Kochi')

        # Other Donor
        self.other_donor = User.objects.create_user(username='donor_bob', password='password123')
        UserProfile.objects.create(user=self.other_donor, role='DONOR', is_verified=True, city='Kochi')

        # 2. Verified NGO 1
        self.ngo1 = User.objects.create_user(username='ngo_care', password='password123')
        UserProfile.objects.create(user=self.ngo1, role='NGO', is_verified=True, city='Kochi')
        NGOProfile.objects.create(
            user=self.ngo1,
            organization_name='Care Foundation',
            registration_number='REG-777',
            contact_person='Brother Joseph',
            is_approved=True
        )

        # 3. Verified NGO 2
        self.ngo2 = User.objects.create_user(username='ngo_hope', password='password123')
        UserProfile.objects.create(user=self.ngo2, role='NGO', is_verified=True, city='Kochi')
        NGOProfile.objects.create(
            user=self.ngo2,
            organization_name='Hope NGO',
            registration_number='REG-888',
            contact_person='Sister Maria',
            is_approved=True
        )

        # 4. Unverified NGO
        self.unverified_ngo = User.objects.create_user(username='ngo_pending', password='password123')
        UserProfile.objects.create(user=self.unverified_ngo, role='NGO', is_verified=False, city='Kochi')
        NGOProfile.objects.create(
            user=self.unverified_ngo,
            organization_name='Pending NGO',
            registration_number='REG-999',
            contact_person='David',
            is_approved=False
        )

        # Category
        self.category = DonationCategory.objects.create(name='Winter Blankets', description='Warm bedding')

    def test_complete_end_to_end_operational_workflow(self):
        # Step 1: Donor creates donation
        self.client.login(username='donor_alice', password='password123')
        create_res = self.client.post(reverse('create_donation'), {
            'title': '20 Warm Fleece Blankets',
            'category': self.category.id,
            'quantity': '20 pieces',
            'description': 'Brand new packed blankets',
            'pickup_address': '45 Fort Kochi',
            'pickup_date': '2026-10-15',
            'pickup_time': '10:00:00',
        })
        self.assertEqual(create_res.status_code, 302)
        donation = Donation.objects.get(title='20 Warm Fleece Blankets')
        self.assertEqual(donation.status, 'AVAILABLE')
        self.client.logout()

        # Step 2: Unverified NGO tries to request -> Blocked
        self.client.login(username='ngo_pending', password='password123')
        blocked_res = self.client.post(reverse('submit_request', kwargs={'donation_id': donation.id}), {
            'message': 'We want these blankets.'
        })
        self.assertEqual(blocked_res.status_code, 302)
        self.assertFalse(DonationRequest.objects.filter(donation=donation, ngo=self.unverified_ngo).exists())
        self.client.logout()

        # Step 3: NGO 1 requests donation -> Sets PENDING and Donation REQUESTED
        self.client.login(username='ngo_care', password='password123')
        req1_res = self.client.post(reverse('submit_request', kwargs={'donation_id': donation.id}), {
            'message': 'We will distribute to 25 destitute elders.'
        })
        self.assertEqual(req1_res.status_code, 302)
        donation.refresh_from_db()
        self.assertEqual(donation.status, 'REQUESTED')
        req1 = DonationRequest.objects.get(donation=donation, ngo=self.ngo1)
        self.assertEqual(req1.status, 'PENDING')

        # Duplicate request by same NGO -> Blocked
        dup_res = self.client.post(reverse('submit_request', kwargs={'donation_id': donation.id}), {
            'message': 'Duplicate attempt'
        })
        self.assertEqual(dup_res.status_code, 302)
        self.assertEqual(DonationRequest.objects.filter(donation=donation, ngo=self.ngo1).count(), 1)
        self.client.logout()

        # Step 4: NGO 2 also requests donation
        self.client.login(username='ngo_hope', password='password123')
        req2_res = self.client.post(reverse('submit_request', kwargs={'donation_id': donation.id}), {
            'message': 'We have a children shelter needing bedding.'
        })
        self.assertEqual(req2_res.status_code, 302)
        req2 = DonationRequest.objects.get(donation=donation, ngo=self.ngo2)
        self.assertEqual(req2.status, 'PENDING')
        self.client.logout()

        # Step 5: Unauthorized user tries to manage request
        self.client.login(username='donor_bob', password='password123')
        unauth_res = self.client.post(reverse('manage_request', kwargs={'request_id': req1.id, 'action': 'approve'}))
        self.assertEqual(unauth_res.status_code, 302)
        req1.refresh_from_db()
        self.assertEqual(req1.status, 'PENDING')
        self.client.logout()

        # Step 6: Donor approves NGO 1's request
        # Sets req1=APPROVED, donation=APPROVED, and automatically rejects req2
        self.client.login(username='donor_alice', password='password123')
        approve_res = self.client.post(reverse('manage_request', kwargs={'request_id': req1.id, 'action': 'approve'}))
        self.assertEqual(approve_res.status_code, 302)
        donation.refresh_from_db()
        req1.refresh_from_db()
        req2.refresh_from_db()
        self.assertEqual(donation.status, 'APPROVED')
        self.assertEqual(req1.status, 'APPROVED')
        self.assertEqual(req2.status, 'REJECTED')
        self.client.logout()

        # Step 7: NGO 1 marks collected
        self.client.login(username='ngo_care', password='password123')
        collect_res = self.client.post(reverse('mark_collected', kwargs={'request_id': req1.id}))
        self.assertEqual(collect_res.status_code, 302)
        donation.refresh_from_db()
        req1.refresh_from_db()
        self.assertEqual(donation.status, 'COLLECTED')
        self.assertEqual(req1.status, 'COLLECTED')
        self.client.logout()

        # Step 8: Donor confirms final handoff / completion
        self.client.login(username='donor_alice', password='password123')
        complete_res = self.client.post(reverse('mark_completed', kwargs={'request_id': req1.id}))
        self.assertEqual(complete_res.status_code, 302)
        donation.refresh_from_db()
        req1.refresh_from_db()
        self.assertEqual(donation.status, 'COMPLETED')
        self.assertEqual(req1.status, 'COMPLETED')

    def test_rejection_reverts_to_available_if_no_other_requests(self):
        donation = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Single Request Item',
            quantity='1 box',
            pickup_address='Edappally',
            status='AVAILABLE'
        )
        self.client.login(username='ngo_care', password='password123')
        self.client.post(reverse('submit_request', kwargs={'donation_id': donation.id}), {
            'message': 'Need this'
        })
        donation.refresh_from_db()
        self.assertEqual(donation.status, 'REQUESTED')
        req = DonationRequest.objects.get(donation=donation, ngo=self.ngo1)
        self.client.logout()

        # Donor rejects
        self.client.login(username='donor_alice', password='password123')
        self.client.post(reverse('manage_request', kwargs={'request_id': req.id, 'action': 'reject'}))
        req.refresh_from_db()
        donation.refresh_from_db()
        self.assertEqual(req.status, 'REJECTED')
        self.assertEqual(donation.status, 'AVAILABLE')
