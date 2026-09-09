from django.db import models

from myapp.base.models import BaseModel

from .menu_category import MenuCategory


class MenuItem(BaseModel):
    """
    A single dish/drink that can be ordered off the menu.
    """
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Menu item"
        verbose_name_plural = "Menu items"
        ordering = ["category", "name"]

    def __str__(self):
        return self.name
