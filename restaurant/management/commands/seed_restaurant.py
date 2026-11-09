from django.core.management.base import BaseCommand

from restaurant.models import MenuCategory, MenuItem, Restaurant, RestaurantTable

# Sourced from the evaluation knowledge base (rag/evaluation/data/kb_source/
# restaurant_menu.md + allergen_guide.md): "The Garden Table". Only what those two documents
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
            ("Roasted tomato soup", "7.00", "Slow-roasted tomatoes, basil oil and toasted sourdough. Vegetarian. Contains gluten (sourdough)."),
            ("Garden salad", "8.00", "Mixed greens, cucumber, tomato, carrots and house vinaigrette. Vegan."),
            ("Hummus plate", "9.00", "Chickpea hummus with tahini, pickled vegetables and flatbread. Vegan. Contains sesame and gluten."),
            ("Crispy calamari", "11.00", "Lightly battered squid with lemon aioli. Contains shellfish, gluten and egg."),
        ],
    ),
    (
        "Main Courses",
        [
            ("Mushroom pasta", "16.00", "Fresh tagliatelle, roasted mushrooms, parmesan and cream sauce. Vegetarian. Contains gluten, dairy and egg."),
            ("Vegetable curry", "15.00", "Seasonal vegetables and chickpeas in coconut and tomato curry, with jasmine rice. Vegan, gluten-free."),
            ("Garden burger", "15.00", "Black bean and beet patty, cheddar, herb mayo, brioche bun, fries. Vegetarian; vegan on request."),
            ("Grilled chicken bowl", "17.00", "Grilled chicken, roasted vegetables, rice and herb sauce. Gluten-free."),
            ("Grilled salmon", "21.00", "Salmon with lemon butter, crushed potatoes and green beans. Contains fish and dairy."),
            ("Steak frites", "26.00", "Grass-fed sirloin, garlic butter, fries and watercress. Contains dairy."),
        ],
    ),
    (
        "Desserts",
        [
            ("Lemon cheesecake", "8.00", "Contains gluten, dairy and egg."),
            ("Chocolate almond torte", "9.00", "Flourless. Contains tree nuts (almonds), egg and dairy."),
            ("Vanilla ice cream", "6.00", "Contains dairy and egg."),
            ("Seasonal fruit sorbet", "6.00", "Vegan, gluten-free."),
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
