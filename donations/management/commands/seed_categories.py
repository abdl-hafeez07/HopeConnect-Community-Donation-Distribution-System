from django.core.management.base import BaseCommand
from donations.models import Category


class Command(BaseCommand):
    help = "Seed initial donation categories into the database"

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Cooked Food & Meals',
                'description': 'Surplus cooked food from events, restaurants, and households suitable for immediate distribution.',
                'icon': 'bi-egg-fried',
            },
            {
                'name': 'Raw Groceries & Rations',
                'description': 'Grains, pulses, rice, oil, canned food, and dry ration kits.',
                'icon': 'bi-basket2-fill',
            },
            {
                'name': 'Clothes & Footwear',
                'description': 'Clean, wearable apparel, winter wear, blankets, and shoes for adults and children.',
                'icon': 'bi-tag-fill',
            },
            {
                'name': 'Books & Educational Material',
                'description': 'School textbooks, notebooks, stationery, story books, and study guides.',
                'icon': 'bi-book-half',
            },
            {
                'name': 'Medical & Hygiene Essentials',
                'description': 'First-aid kits, sanitary pads, hygiene kits, and unused unexpired OTC medical supplies.',
                'icon': 'bi-capsule',
            },
            {
                'name': 'Toys & Child Care',
                'description': 'Toys, board games, baby clothing, and children care items.',
                'icon': 'bi-emoji-smile-fill',
            },
        ]

        created_count = 0
        for cat in categories:
            obj, created = Category.objects.get_or_create(
                name=cat['name'],
                defaults={
                    'description': cat['description'],
                    'icon': cat['icon'],
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created category: {obj.name}"))
            else:
                self.stdout.write(f"Category already exists: {obj.name}")

        self.stdout.write(self.style.SUCCESS(f"Done! Created {created_count} new categories."))
