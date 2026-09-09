from django.db import models

from myapp.base.models import BaseModel

from .restaurant import Restaurant


class MenuCategory(BaseModel):
    """
    Grouping for menu items, e.g. Starters, Main course, Desserts, Drinks.
    """
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="menu_categories")
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order on the menu")

    class Meta:
        verbose_name = "Menu category"
        verbose_name_plural = "Menu categories"
        ordering = ["restaurant", "order", "name"]

    def __str__(self):
        return self.name
