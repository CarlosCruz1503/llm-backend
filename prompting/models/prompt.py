from django.db import models

OutputType = {
    "summarize": "summarize",
    "classify": "classify",
    "extract_keywords": "extract_keywords"
}
ProviderChoices = {
    # "claude": "claude",   # not implemented yet, see providers/LLMs/claude.py
    "gemini": "gemini",
    # "openai": "openai",   # not implemented yet, see providers/LLMs/open_ai.py
    "openrouter":"openrouter"
}

ThinkingLevelChoices = {
    "low": "low",
    "medium": "medium",
    "high": "high",
}
 
class PromptModel(models.Model):
    
    created_at = models.DateField(auto_now_add=True, verbose_name="Date Time Created At")
    input = models.TextField(max_length=2000, null=False, blank=False)
    output_type = models.CharField(choices=OutputType)
    output = models.TextField(max_length=2000, null=True, blank=True)
    output_dict =  models.JSONField(default=dict, blank=True) 
    error = models.TextField(max_length=2000, null=True, blank=True)
    response_code = models.TextField(max_length=128, null=True, blank=True)
    status = models.TextField(max_length=128, null=True, blank=True)
    request_id = models.TextField(max_length=128, null=True, blank=True)
    model = models.TextField(max_length=128, null=True, blank=True)
    provider = models.CharField(choices=ProviderChoices)
    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    total_tokens = models.IntegerField(null=True, blank=True)
    thinking_level = models.CharField(choices=ThinkingLevelChoices, default="low")
    
    class Meta:
        verbose_name = ("Prompt")
        verbose_name_plural = ("Prompts")
        ordering = ["-created_at"]

    # def __str__(self):
    #     return self.output

