from django.core.management.base import BaseCommand

from restaurant.models import MenuCategory, MenuItem, Restaurant, RestaurantTable

# Sourced from the sample knowledge base PDFs (restaurant_menu.pdf +
# allergen_guide.pdf): "The Garden Table". Only what those two documents
# actually state is modeled here — no invented address/phone/email, and no
# deeper "why"/policy content, since that belongs in the RAG pipeline as
# embedded documents, not in these relational tables (see Restaurant's
# docstring in restaurant/models/restaurant.py).
RESTAURANT_NAME = "The Garden Table"

# (category name, [(item name, price, description), ...])
MENU = [
    (
        "Starters",
        [
            ("Roasted tomato soup", "7.00", "Served with toasted sourdough and basil oil. Vegetarian. Contains gluten (sourdough)."),
            ("Crispy calamari", "11.00", "Served with lemon and garlic aioli. Contains shellfish."),
            ("Garden salad", "8.00", "Mixed greens, cucumber, tomato, carrots, and house vinaigrette. Vegetarian."),
        ],
    ),
    (
        "Main Courses",
        [
            ("Grilled chicken bowl", "16.00", "Grilled chicken, roasted vegetables, rice, and herb sauce."),
            ("Mushroom pasta", "15.00", "Pasta with wild mushrooms, parmesan, garlic, and cream sauce. Vegetarian. Contains dairy and gluten (pasta)."),
            ("Grilled salmon", "21.00", "Salmon with roasted potatoes, seasonal vegetables, and lemon butter. Contains fish."),
            ("Vegetable curry", "14.00", "Chickpeas, seasonal vegetables, coconut milk, and jasmine rice. Vegetarian."),
        ],
    ),
    (
        "Desserts",
        [
            ("Chocolate cake", "8.00", ""),
            ("Lemon cheesecake", "8.00", ""),
            ("Seasonal fruit", "6.00", ""),
            ("Vanilla ice cream", "5.00", ""),
        ],
    ),
]

# A handful of tables purely so there's something to point Reservations at
# in manual/API testing — not sourced from any PDF, just example data.
EXAMPLE_TABLES = [
    # (number, capacity, location)
    (1, 2, "indoor"),
    (2, 4, "indoor"),
    (3, 4, "outdoor"),
    (4, 6, "outdoor"),
    (5, 2, "bar"),
]


class Command(BaseCommand):
    help = "Seeds the restaurant app with 'The Garden Table' sample data (restaurant, menu, and a few example tables)."

    def handle(self, *args, **options):
        restaurant, created = Restaurant.objects.update_or_create(
            name=RESTAURANT_NAME,
            defaults={},
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Found existing'} restaurant '{restaurant.name}' (id={restaurant.pk})"
        ))

        for order, (category_name, items) in enumerate(MENU):
            category, created = MenuCategory.objects.update_or_create(
                restaurant=restaurant,
                name=category_name,
                defaults={"order": order},
            )
            self.stdout.write(f"  {'Created' if created else 'Found'} category '{category.name}'")

            for name, price, description in items:
                item, created = MenuItem.objects.update_or_create(
                    category=category,
                    name=name,
                    defaults={"price": price, "description": description, "is_available": True},
                )
                self.stdout.write(f"    {'Created' if created else 'Found'} item '{item.name}' (${item.price})")

        for number, capacity, location in EXAMPLE_TABLES:
            table, created = RestaurantTable.objects.update_or_create(
                restaurant=restaurant,
                number=number,
                defaults={"capacity": capacity, "location": location},
            )
            self.stdout.write(f"  {'Created' if created else 'Found'} table {table.number} (seats {table.capacity}, {table.location})")

        self.stdout.write(self.style.SUCCESS("Done seeding restaurant data."))
