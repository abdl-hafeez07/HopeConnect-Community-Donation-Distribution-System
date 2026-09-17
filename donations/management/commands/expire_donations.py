from django.core.management.base import BaseCommand
from django.utils import timezone
from donations.models import Donation


class Command(BaseCommand):
    help = 'Quietly marks past-due available donations as EXPIRED.'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_count = Donation.objects.filter(
            status='AVAILABLE',
            expiry_date__isnull=False,
            expiry_date__lt=now
        ).update(status='EXPIRED')

        self.stdout.write(
            self.style.SUCCESS(f"Quiet auto-expiry completed: {expired_count} donation(s) expired.")
        )
