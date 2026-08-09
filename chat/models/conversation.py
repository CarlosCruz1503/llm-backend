from django.db import models
from myapp.base import BaseModel
class Conversation(BaseModel):
    """
    Conversation model.
    """
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = ("Conversation")
        verbose_name_plural = ("Conversations")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title