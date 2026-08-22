from django.db import models

from myapp.base import UserModel
from prompting.constants import DEFAULT_THINKING_LEVEL, ProviderChoices, ThinkingLevelChoices


class OutputType(models.TextChoices):
    SUMMARIZE = "summarize", "Summarize"
    CLASSIFY = "classify", "Classify"
    EXTRACT_KEYWORDS = "extract_keywords", "Extract keywords"


class PromptModel(UserModel):

    input = models.TextField(max_length=2000, null=False, blank=False)
    output_type = models.CharField(choices=OutputType.choices)
    output = models.TextField(max_length=2000, null=True, blank=True)
    output_dict = models.JSONField(default=dict, blank=True)
    error = models.TextField(max_length=2000, null=True, blank=True)
    response_code = models.CharField(max_length=128, null=True, blank=True)
    status = models.CharField(max_length=128, null=True, blank=True)
    request_id = models.CharField(max_length=128, null=True, blank=True)
    model = models.CharField(max_length=128, null=True, blank=True)
    provider = models.CharField(choices=ProviderChoices.choices)
    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    total_tokens = models.IntegerField(null=True, blank=True)
    thinking_level = models.CharField(choices=ThinkingLevelChoices.choices, default=DEFAULT_THINKING_LEVEL)

    class Meta:
        verbose_name = "Prompt"
        verbose_name_plural = "Prompts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.provider}] {self.output_type} #{self.pk}"
