from django.db import models

from myapp.base import UserModel
from restaurant.constants import DEFAULT_RESERVATION_STATUS, ReservationStatusChoices

from .restaurant import Restaurant
from .table import RestaurantTable


class Reservation(UserModel):
    """
    A customer's booking for a table at a given date/time. Owned by the
    staff user (via UserModel) who took/created the booking.
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="reservations")
    table = models.ForeignKey(
        RestaurantTable, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservations",
        help_text="Table assigned to the reservation, if any",
    )
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=32, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    party_size = models.PositiveIntegerField(default=1)
    reservation_date = models.DateTimeField()
    status = models.CharField(max_length=32, choices=ReservationStatusChoices.choices, default=DEFAULT_RESERVATION_STATUS)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"
        ordering = ["-reservation_date"]

    def __str__(self):
        return f"{self.customer_name} - {self.reservation_date}"
