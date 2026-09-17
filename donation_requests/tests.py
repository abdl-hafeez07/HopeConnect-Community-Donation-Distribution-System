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

    def test_ngo_contact_confirmation_and_privacy_workflow(self):
        donation = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Warm Blankets Bulk',
            quantity='50 blankets',
            pickup_address='Edappally North',
            status='AVAILABLE'
        )

        # NGO visits request form via accept_request URL - checks form is loaded with pre-filled details
        self.client.login(username='ngo_care', password='password123')
        form_res = self.client.get(reverse('accept_request', kwargs={'donation_id': donation.id}))
        self.assertEqual(form_res.status_code, 200)
        self.assertContains(form_res, 'Confirm NGO Contact Details for Donor')
        self.assertContains(form_res, 'Brother Joseph')

        # NGO confirms/updates contact details
        submit_res = self.client.post(reverse('accept_request', kwargs={'donation_id': donation.id}), {
            'message': 'We distribute to night shelter residents.',
            'contact_person': 'Brother Joseph Updated',
            'contact_phone': '+91 98765 43210',
            'contact_email': 'joseph@care.org',
            'pickup_notes': 'Can collect with our cargo van tomorrow 10am'
        })
        self.assertEqual(submit_res.status_code, 302)
        req = DonationRequest.objects.get(donation=donation, ngo=self.ngo1)
        self.assertEqual(req.contact_person, 'Brother Joseph Updated')
        self.assertEqual(req.contact_phone, '+91 98765 43210')
        self.assertEqual(req.contact_email, 'joseph@care.org')
        self.assertEqual(req.pickup_notes, 'Can collect with our cargo van tomorrow 10am')
        self.client.logout()

        # Donor views review page and dashboard BEFORE approval: contact info must be hidden
        self.client.login(username='donor_alice', password='password123')
        review_res = self.client.get(reverse('review_requests', kwargs={'donation_id': donation.id}))
        self.assertEqual(review_res.status_code, 200)
        self.assertContains(review_res, 'Private NGO contact information is safeguarded')
        self.assertNotContains(review_res, '+91 98765 43210')
        self.assertNotContains(review_res, 'joseph@care.org')

        dash_res = self.client.get(reverse('dashboard:donor_dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertNotContains(dash_res, '+91 98765 43210')
        self.assertNotContains(dash_res, 'joseph@care.org')

        # Donor approves the request
        approve_res = self.client.post(reverse('approve_request', kwargs={'request_id': req.id}))
        self.assertEqual(approve_res.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, 'APPROVED')

        # Donor views review page AFTER approval: confirmed contact details must be visible
        review_res_after = self.client.get(reverse('review_requests', kwargs={'donation_id': donation.id}))
        self.assertContains(review_res_after, 'Confirmed NGO Contact Information')
        self.assertContains(review_res_after, 'Brother Joseph Updated')
        self.assertContains(review_res_after, '+91 98765 43210')
        self.assertContains(review_res_after, 'joseph@care.org')
        self.assertContains(review_res_after, 'Can collect with our cargo van tomorrow 10am')

        # Donor views donation detail: handover details card reveals confirmed NGO contact
        detail_res = self.client.get(reverse('donation_detail', kwargs={'pk': donation.id}))
        self.assertContains(detail_res, 'Confirmed NGO Contact')
        self.assertContains(detail_res, '+91 98765 43210')
        self.assertContains(detail_res, 'joseph@care.org')

        # Donor views donor dashboard AFTER approval: reveals confirmed NGO contact in Approved Handovers
        dash_res_after = self.client.get(reverse('dashboard:donor_dashboard'))
        self.assertContains(dash_res_after, 'Approved Handovers & Confirmed NGO Contacts')
        self.assertContains(dash_res_after, 'Brother Joseph Updated')
        self.assertContains(dash_res_after, '+91 98765 43210')
        self.assertContains(dash_res_after, 'joseph@care.org')

        # Other donor cannot access review page of Alice's donation
        self.client.login(username='donor_bob', password='password123')
        bob_res = self.client.get(reverse('review_requests', kwargs={'donation_id': donation.id}))
        self.assertEqual(bob_res.status_code, 404)

    def test_cancelled_status_badge_and_filter(self):
        donation = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Excess Ration Kits',
            quantity='10 kits',
            pickup_address='Edappally North',
            status='AVAILABLE'
        )
        self.client.login(username='donor_alice', password='password123')
        cancel_res = self.client.get(reverse('cancel_donation', kwargs={'pk': donation.id}))
        self.assertEqual(cancel_res.status_code, 302)
        donation.refresh_from_db()
        self.assertEqual(donation.status, 'CANCELLED')

        # Check my_donations view renders Cancelled badge
        my_donations_res = self.client.get(reverse('my_donations') + '?status=CANCELLED')
        self.assertEqual(my_donations_res.status_code, 200)
        self.assertContains(my_donations_res, 'badge-cancelled')
        self.assertContains(my_donations_res, 'Cancelled')

