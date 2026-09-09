from django.db import models

from myapp.base.models import BaseModel
from restaurant.constants import DEFAULT_TABLE_LOCATION, DEFAULT_TABLE_STATUS, TableLocationChoices, TableStatusChoices

from .restaurant import Restaurant


class RestaurantTable(BaseModel):
    """
    A physical table on the floor plan that a Reservation can be assigned to.
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="tables")
    number = models.PositiveIntegerField(help_text="Table number as shown on the floor plan")
    capacity = models.PositiveIntegerField(help_text="Number of guests the table seats")
    location = models.CharField(max_length=32, choices=TableLocationChoices.choices, default=DEFAULT_TABLE_LOCATION)
    status = models.CharField(max_length=32, choices=TableStatusChoices.choices, default=DEFAULT_TABLE_STATUS)

    class Meta:
        verbose_name = "Table"
        verbose_name_plural = "Tables"
        ordering = ["restaurant", "number"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "number"], name="unique_table_number_per_restaurant"),
        ]

    def __str__(self):
        return f"Table {self.number} ({self.restaurant.name})"
