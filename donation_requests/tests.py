from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile, NGOProfile, VolunteerProfile
from donations.models import Category, Donation
from donation_requests.models import DonationRequest, DeliveryAssignment


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

        # 3. Volunteer (Verified)
        self.vol = User.objects.create_user(username='vol_bob', password='password123')
        UserProfile.objects.create(user=self.vol, role='Volunteer', is_verified=True, city='Kochi')
        VolunteerProfile.objects.create(
            user=self.vol,
            vehicle_type='Car',
            availability_status='Available',
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
            'message': 'We will prepare community meals for 25 destitute elders.'
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
            {'donor_notes': 'Happy to support your community kitchen!'}
        )
        self.assertEqual(approve_res.status_code, 302)
        donation.refresh_from_db()
        request_obj.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_APPROVED)
        self.assertEqual(request_obj.status, DonationRequest.STATUS_APPROVED)

        # Verify DeliveryAssignment was auto-created
        assignment = DeliveryAssignment.objects.get(donation=donation)
        self.assertIsNone(assignment.volunteer)
        self.assertEqual(assignment.status, DeliveryAssignment.STATUS_ASSIGNED)
        self.client.logout()

        # Step 4: Volunteer logs in, checks available pickups, and claims it
        self.client.login(username='vol_bob', password='password123')
        pickups_page = self.client.get(reverse('available_pickups'))
        self.assertContains(pickups_page, '20 Warm Fleece Blankets')

        claim_res = self.client.get(reverse('claim_pickup', kwargs={'assignment_id': assignment.id}))
        self.assertEqual(claim_res.status_code, 302)
        assignment.refresh_from_db()
        donation.refresh_from_db()
        self.assertEqual(assignment.volunteer, self.vol)
        self.assertEqual(donation.status, Donation.STATUS_PICKUP_SCHEDULED)

        # Step 5: Volunteer confirms pickup from donor
        pickup_update = self.client.post(
            reverse('update_delivery', kwargs={'assignment_id': assignment.id}),
            {
                'status': DeliveryAssignment.STATUS_PICKED_UP,
                'recipient_confirmation_name': '',
                'delivery_notes': 'Loaded into vehicle trunk safely.',
            }
        )
        self.assertEqual(pickup_update.status_code, 302)
        assignment.refresh_from_db()
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_PICKED_UP)

        # Step 6: Volunteer confirms delivery to NGO
        delivered_update = self.client.post(
            reverse('update_delivery', kwargs={'assignment_id': assignment.id}),
            {
                'status': DeliveryAssignment.STATUS_DELIVERED,
                'recipient_confirmation_name': 'Brother Joseph (Director)',
                'delivery_notes': 'Handed over at Care Foundation shelter.',
            }
        )
        self.assertEqual(delivered_update.status_code, 302)
        assignment.refresh_from_db()
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_DELIVERED)
        self.assertEqual(assignment.status, DeliveryAssignment.STATUS_DELIVERED)
        self.assertIsNotNone(assignment.delivered_at)
        self.client.logout()

        # Step 7: Recipient NGO logs in and confirms receipt of delivery
        self.client.login(username='ngo_care', password='password123')
        confirm_res = self.client.post(
            reverse('confirm_receipt', kwargs={'assignment_id': assignment.id}),
            {'receipt_notes': 'All 20 blankets verified and distributed to shelter residents.'}
        )
        self.assertEqual(confirm_res.status_code, 302)
        assignment.refresh_from_db()
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_COMPLETED)
        self.assertEqual(assignment.status, DeliveryAssignment.STATUS_COMPLETED)
        self.assertIn("NGO Confirmation", assignment.delivery_notes)
