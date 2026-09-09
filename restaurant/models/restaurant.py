from django.db import models

from myapp.base.models import BaseModel


class Restaurant(BaseModel):
    """
    Basic restaurant identity/contact info — just enough for menu, tables
    and reservations to hang off of. Deeper knowledge about the restaurant
    (story, policies, FAQs, etc.) is deliberately NOT modeled here: that
    lives in the RAG pipeline as embedded documents, searched separately.
    """
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"
        ordering = ["name"]

    def __str__(self):
        return self.name
