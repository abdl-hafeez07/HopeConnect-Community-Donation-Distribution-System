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

    def test_flexible_delivery_options_creation(self):
        self.client.login(username='donor_test', password='password123')
        post_res = self.client.post(reverse('create_donation'), {
            'title': 'School Notebooks & Storybooks',
            'category': self.category.id,
            'quantity': '2 books',
            'delivery_option': 'DONOR_DELIVERY',
            'dropoff_location': 'Local Reading Room & Community Hub',
            'pickup_address': 'Kaloor, Kochi',
            'pickup_date': '2026-11-01',
            'pickup_time': '14:00:00',
        })
        self.assertEqual(post_res.status_code, 302)
        don = Donation.objects.get(title='School Notebooks & Storybooks')
        self.assertEqual(don.delivery_option, 'DONOR_DELIVERY')
        self.assertEqual(don.dropoff_location, 'Local Reading Room & Community Hub')
        self.assertTrue(don.is_donor_delivery)
        self.assertFalse(don.is_ngo_pickup)
        self.assertTrue(don.is_small_donation)

        # Verify detail page displays transfer method
        detail_res = self.client.get(reverse('donation_detail', kwargs={'pk': don.id}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, 'Donor will deliver / drop off')
        self.assertContains(detail_res, 'Local Reading Room &amp; Community Hub')

    def test_micro_donation_detection(self):
        d_micro_books = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='2 Children Books',
            quantity='2 books',
            pickup_address='Edappally',
            status='AVAILABLE'
        )
        self.assertTrue(d_micro_books.is_small_donation)

        d_micro_meal = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Fresh Dinner Packet',
            quantity='1 meal',
            pickup_address='Edappally',
            status='AVAILABLE'
        )
        self.assertTrue(d_micro_meal.is_small_donation)

        d_bulk = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Rice Sacks Commercial',
            quantity='100 kg bulk bags',
            pickup_address='Edappally',
            status='AVAILABLE'
        )
        self.assertFalse(d_bulk.is_small_donation)

    def test_delivery_filtering_and_hyperlocal_matching(self):
        # Other donor in Trivandrum
        trivandrum_donor = User.objects.create_user(username='donor_tvm', password='password123')
        UserProfile.objects.create(user=trivandrum_donor, role='DONOR', is_verified=True, city='Trivandrum')

        # Kochi item (NGO pickup)
        d_kochi = Donation.objects.create(
            donor=self.donor, # city=Kochi
            category=self.category,
            title='Kochi Pickup Care Package',
            quantity='10 kg',
            delivery_option='NGO_PICKUP',
            pickup_address='MG Road Kochi',
            status='AVAILABLE'
        )

        # Trivandrum item (Donor delivery)
        d_tvm = Donation.objects.create(
            donor=trivandrum_donor, # city=Trivandrum
            category=self.category,
            title='Trivandrum Drop-off Blankets',
            quantity='15 blankets',
            delivery_option='DONOR_DELIVERY',
            dropoff_location='Trivandrum Relief Hub',
            pickup_address='Palayam TVM',
            status='AVAILABLE'
        )

        # Filter by delivery option: DONOR_DELIVERY
        res_del = self.client.get(reverse('donations_list'), {'delivery_option': 'DONOR_DELIVERY'})
        self.assertContains(res_del, 'Trivandrum Drop-off Blankets')
        self.assertNotContains(res_del, 'Kochi Pickup Care Package')

        # Filter by delivery option: NGO_PICKUP
        res_pick = self.client.get(reverse('donations_list'), {'delivery_option': 'NGO_PICKUP'})
        self.assertContains(res_pick, 'Kochi Pickup Care Package')
        self.assertNotContains(res_pick, 'Trivandrum Drop-off Blankets')

        # Logged in as verified_ngo (Kochi NGO), apply hyperlocal match filter
        self.client.login(username='verified_ngo', password='password123')
        res_hyper = self.client.get(reverse('donations_list'), {'hyperlocal': '1'})
        self.assertContains(res_hyper, 'Kochi Pickup Care Package')
        self.assertNotContains(res_hyper, 'Trivandrum Drop-off Blankets')
        self.client.logout()

    def test_quiet_auto_expiry(self):
        # Create expired available donation
        past_time = timezone.now() - timedelta(days=1)
        expired_donation = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Yesterday Perishable Food',
            quantity='10 meals',
            expiry_date=past_time,
            pickup_address='Kaloor',
            status='AVAILABLE'
        )
        self.assertEqual(expired_donation.status, 'AVAILABLE')

        # Visiting donation_list quietly auto-expires the past-due item
        res = self.client.get(reverse('donations_list'))
        self.assertEqual(res.status_code, 200)
        self.assertNotContains(res, 'Yesterday Perishable Food')

        expired_donation.refresh_from_db()
        self.assertEqual(expired_donation.status, 'EXPIRED')

