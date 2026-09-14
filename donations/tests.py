from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError

from accounts.models import UserProfile
from donations.models import Category, Donation, FoodDetail, DonationStatusHistory


class DonationsModelAndViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.donor = User.objects.create_user(
            username='donor_test',
            password='password123'
        )
        UserProfile.objects.create(user=self.donor, role='Donor', is_verified=True)

        self.category = Category.objects.create(
            name='Cooked Food & Meals',
            description='Surplus food'
        )

    def test_donation_creation_and_status_change(self):
        donation = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='25 Meals Rice & Curry',
            description='Freshly cooked lunch packets',
            quantity='25 packets',
            pickup_address='123 Marine Drive',
            city='Kochi'
        )
        self.assertEqual(donation.status, Donation.STATUS_AVAILABLE)
        self.assertTrue(donation.is_available)

        # Change status and verify history record
        donation.change_status(
            Donation.STATUS_REQUESTED,
            user=self.donor,
            remarks='NGO requested donation'
        )
        self.assertEqual(donation.status, Donation.STATUS_REQUESTED)
        history = DonationStatusHistory.objects.filter(donation=donation)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().status, Donation.STATUS_REQUESTED)

    def test_food_detail_validation(self):
        donation = Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Vegetable Biryani',
            description='Event excess',
            quantity='50 boxes',
            pickup_address='Panampilly Nagar',
            city='Kochi'
        )
        future_time = timezone.now() + timedelta(hours=4)
        food_detail = FoodDetail.objects.create(
            donation=donation,
            food_type='Cooked Meals',
            expiry_time=future_time,
            dietary_type='Vegetarian'
        )
        self.assertFalse(food_detail.is_expired)

        # Test past expiry validation
        past_food = FoodDetail(
            donation=donation,
            food_type='Cooked Meals',
            expiry_time=timezone.now() - timedelta(hours=1),
            dietary_type='Vegetarian'
        )
        with self.assertRaises(ValidationError):
            past_food.clean()

    def test_donation_catalog_and_filter(self):
        Donation.objects.create(
            donor=self.donor,
            category=self.category,
            title='Sandwiches',
            description='Fresh sandwiches',
            quantity='30 packs',
            pickup_address='Kaloor',
            city='Kochi',
            status=Donation.STATUS_AVAILABLE
        )
        response = self.client.get(reverse('donations_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sandwiches')

        # Filter by query
        search_res = self.client.get(reverse('donations_list'), {'q': 'Sandwiches'})
        self.assertContains(search_res, 'Sandwiches')

        no_match = self.client.get(reverse('donations_list'), {'q': 'NonExistentItem'})
        self.assertNotContains(no_match, 'Sandwiches')
