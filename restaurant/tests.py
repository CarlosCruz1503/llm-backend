from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase

from restaurant.models import MenuCategory, MenuItem, Reservation, Restaurant, RestaurantTable
from restaurant.services.menu import MenuService
from restaurant.services.reservation import NoTableAvailableError, ReservationService, parse_reservation_datetime


class RestaurantTestCase(TestCase):
    """UserModel.save() (myapp/base/models.py) falls back to the first
    superuser when there's no request-bound current user (true for every
    test, since crum's current-user is only set inside the request/response
    cycle) — Reservation creates in these tests need one to exist, or the
    not-null `user` FK fails.
    """

    def setUp(self):
        User.objects.create_superuser(username="tester", email="tester@example.com", password="password123")
        self.restaurant = Restaurant.objects.create(name="La Buena Mesa")


class MenuTests(RestaurantTestCase):

    def test_menu_item_belongs_to_a_category_of_the_restaurant(self):
        category = MenuCategory.objects.create(restaurant=self.restaurant, name="Starters")
        item = MenuItem.objects.create(category=category, name="Guacamole", price="8.50")

        self.assertEqual(item.category.restaurant, self.restaurant)
        self.assertTrue(item.is_available)


class RestaurantTableTests(RestaurantTestCase):

    def test_table_number_is_unique_per_restaurant(self):
        RestaurantTable.objects.create(restaurant=self.restaurant, number=1, capacity=4)

        with self.assertRaises(IntegrityError):
            RestaurantTable.objects.create(restaurant=self.restaurant, number=1, capacity=2)


class ReservationTests(RestaurantTestCase):

    def test_reservation_can_be_created_without_a_table_assigned(self):
        reservation = Reservation.objects.create(
            restaurant=self.restaurant,
            customer_name="Jane Doe",
            party_size=2,
            reservation_date="2026-09-05T20:00:00Z",
        )

        self.assertIsNone(reservation.table)
        self.assertEqual(reservation.status, "pending")


class ReservationServiceTests(RestaurantTestCase):

    def setUp(self):
        super().setUp()
        self.small_table = RestaurantTable.objects.create(restaurant=self.restaurant, number=1, capacity=2)
        self.big_table = RestaurantTable.objects.create(restaurant=self.restaurant, number=2, capacity=6)
        self.service = ReservationService()

    def test_assigns_the_smallest_table_that_fits_the_party(self):
        reservation = self.service.create_reservation(
            restaurant=self.restaurant,
            reservation_date=parse_reservation_datetime("2026-09-05 20:00"),
            party_size=2,
            customer_name="Jane Doe",
        )

        self.assertEqual(reservation.table, self.small_table)

    def test_rejects_a_second_reservation_in_the_same_hour_for_the_same_table(self):
        # Only one table fits a party of 6, so the second booking in the
        # same hour has nowhere to go.
        self.service.create_reservation(
            restaurant=self.restaurant,
            reservation_date=parse_reservation_datetime("2026-09-05 20:00"),
            party_size=6,
            customer_name="Jane Doe",
        )

        with self.assertRaises(NoTableAvailableError):
            self.service.create_reservation(
                restaurant=self.restaurant,
                reservation_date=parse_reservation_datetime("2026-09-05 20:45"),
                party_size=6,
                customer_name="John Smith",
            )

    def test_allows_a_reservation_for_the_same_table_in_a_different_hour(self):
        self.service.create_reservation(
            restaurant=self.restaurant,
            reservation_date=parse_reservation_datetime("2026-09-05 20:00"),
            party_size=6,
            customer_name="Jane Doe",
        )

        reservation = self.service.create_reservation(
            restaurant=self.restaurant,
            reservation_date=parse_reservation_datetime("2026-09-05 21:00"),
            party_size=6,
            customer_name="John Smith",
        )

        self.assertEqual(reservation.table, self.big_table)

    def test_cancelled_reservations_free_up_the_table(self):
        existing = self.service.create_reservation(
            restaurant=self.restaurant,
            reservation_date=parse_reservation_datetime("2026-09-05 20:00"),
            party_size=6,
            customer_name="Jane Doe",
        )
        existing.status = "cancelled"
        existing.save(update_fields=["status"])

        reservation = self.service.create_reservation(
            restaurant=self.restaurant,
            reservation_date=parse_reservation_datetime("2026-09-05 20:30"),
            party_size=6,
            customer_name="John Smith",
        )

        self.assertEqual(reservation.table, self.big_table)


class MenuServiceTests(RestaurantTestCase):

    def test_formatted_menu_groups_available_items_by_category(self):
        starters = MenuCategory.objects.create(restaurant=self.restaurant, name="Starters", order=0)
        mains = MenuCategory.objects.create(restaurant=self.restaurant, name="Main Courses", order=1)
        MenuItem.objects.create(category=starters, name="Garden salad", price="8.00", description="Mixed greens.")
        MenuItem.objects.create(category=mains, name="Grilled salmon", price="21.00")
        MenuItem.objects.create(category=mains, name="Off-menu special", price="99.00", is_available=False)

        menu = MenuService().get_formatted_menu(self.restaurant)

        self.assertIn(self.restaurant.name, menu)
        self.assertIn("Starters", menu)
        self.assertIn("Garden salad — $8.00: Mixed greens.", menu)
        self.assertIn("Grilled salmon — $21.00", menu)
        # Unavailable items are left off the menu shared with customers.
        self.assertNotIn("Off-menu special", menu)
