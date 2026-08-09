import os

from django.db import models


class ProviderChoices(models.TextChoices):
    GEMINI = "gemini", "Gemini"
    OPENROUTER = "openrouter", "OpenRouter"
    # CLAUDE = "claude", "Claude"      # not implemented yet, see providers/LLMs/claude.py
    # OPENAI = "openai", "OpenAI"      # not implemented yet, see providers/LLMs/open_ai.py


class ThinkingLevelChoices(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


DEFAULT_THINKING_LEVEL = ThinkingLevelChoices.LOW

MODEL_GEMINI = os.environ.get("GEMINI_AI_MODEL")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")

SYSTEM_INSTRUCTION_FOR_CHAT = "You are a helpful assistant that can answer questions and help with tasks."

MAX_TOKENS_FOR_CHAT_CONTEXTS = 4000