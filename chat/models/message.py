from django.db import models

from myapp.base import UserModel
from prompting.constants import DEFAULT_THINKING_LEVEL, ProviderChoices, ThinkingLevelChoices

from .conversation import Conversation


class RoleChoices(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    SYSTEM = "system", "System"


class Message(UserModel):
    """
    Message model.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    content = models.TextField()
    role = models.CharField(max_length=255, choices=RoleChoices.choices, default=RoleChoices.USER)
    provider = models.CharField(max_length=255, choices=ProviderChoices.choices, default=ProviderChoices.GEMINI)
    thinking_level = models.CharField(max_length=255, choices=ThinkingLevelChoices.choices, default=DEFAULT_THINKING_LEVEL)
    model = models.CharField(max_length=255, null=True, blank=True)
    response_code = models.CharField(max_length=128, null=True, blank=True)
    status = models.CharField(max_length=128, null=True, blank=True)
    request_id = models.CharField(max_length=128, null=True, blank=True)
    tokens = models.IntegerField(null=True, blank=True)
    error = models.TextField(max_length=2000, null=True, blank=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["-created_at"]

    def __str__(self):
        return self.content
