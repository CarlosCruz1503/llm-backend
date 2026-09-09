from django.db import models


class TableLocationChoices(models.TextChoices):
    INDOOR = "indoor", "Indoor"
    OUTDOOR = "outdoor", "Outdoor"
    BAR = "bar", "Bar"


DEFAULT_TABLE_LOCATION = TableLocationChoices.INDOOR


class TableStatusChoices(models.TextChoices):
    AVAILABLE = "available", "Available"
    OCCUPIED = "occupied", "Occupied"
    RESERVED = "reserved", "Reserved"
    MAINTENANCE = "maintenance", "Under maintenance"


DEFAULT_TABLE_STATUS = TableStatusChoices.AVAILABLE


class ReservationStatusChoices(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    SEATED = "seated", "Seated"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    NO_SHOW = "no_show", "No show"


DEFAULT_RESERVATION_STATUS = ReservationStatusChoices.PENDING
