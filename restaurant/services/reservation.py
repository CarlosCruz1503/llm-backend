import logging
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from restaurant.constants import ReservationStatusChoices
from restaurant.models import Reservation, RestaurantTable

logger = logging.getLogger(__name__)


class NoTableAvailableError(Exception):
    """Raised when no table can seat the party at the requested hour."""


def parse_reservation_datetime(value):
    """Parse a reservation date/time string (e.g. "2024-07-29 20:00" or
    "2024-07-29T20:00") into a timezone-aware datetime. A string with no UTC
    offset is assumed to already be in the server's configured TIME_ZONE.
    """
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError(f"'{value}' isn't a valid date/time (expected e.g. '2024-07-29 20:00').")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


class ReservationService:
    """Creates reservations without the caller (or the LLM tool on top of
    this) ever picking a specific table: any table free at the requested
    hour and big enough for the party is assigned automatically.
    """

    def is_table_available(self, table, reservation_date):
        """A table is unavailable if it already has a non-cancelled
        reservation anywhere in the same hour (e.g. a 20:15 request
        conflicts with an existing 20:45 reservation at that table).
        """
        hour_start = reservation_date.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)

        return not Reservation.objects.filter(
            table=table,
            reservation_date__gte=hour_start,
            reservation_date__lt=hour_end,
        ).exclude(status=ReservationStatusChoices.CANCELLED).exists()

    def find_available_table(self, restaurant, reservation_date, party_size):
        # Smallest-fitting table first, so a party of 2 doesn't needlessly
        # take the table that a party of 6 might need for the same hour.
        candidate_tables = RestaurantTable.objects.filter(
            restaurant=restaurant, capacity__gte=party_size,
        ).order_by("capacity")

        for table in candidate_tables:
            if self.is_table_available(table, reservation_date):
                return table
        return None

    def create_reservation(
        self, restaurant, reservation_date, party_size, customer_name,
        customer_phone=None, customer_email=None, notes=None,
    ):
        table = self.find_available_table(restaurant, reservation_date, party_size)
        if table is None:
            raise NoTableAvailableError(
                f"No table for {party_size} guest(s) is free around {reservation_date:%Y-%m-%d %H:%M}."
            )

        return Reservation.objects.create(
            restaurant=restaurant,
            table=table,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            party_size=party_size,
            reservation_date=reservation_date,
            notes=notes,
        )
