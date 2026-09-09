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

GEMINI_MODEL = os.environ.get("GEMINI_AI_MODEL")

GEMINI_EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")

OPENROUTER_EMBEDDING_MODEL = os.environ.get("OPENROUTER_EMBEDDING_MODEL")

SYSTEM_INSTRUCTION_FOR_CHAT = "You are a helpful assistant that can answer questions and help with tasks."

MAX_TOKENS_FOR_CHAT_CONTEXTS = 4000

COSINE_DISTANCE_THRESHOLD = os.getenv("COSINE_DISTANCE_THRESHOLD", "0.45")

ADMIN_LIST_DISPLAY = ("created_at", "updated_at", "deleted")

class TokenModelChoices(models.TextChoices):
    o200k_base= "o200k_base"
    cl100k_base = "cl100k_base"
    p50k_base = "p50k_base"
    r50k_base = "r50k_base"
    
DEFAULT_TOKEN_MODEL = TokenModelChoices.cl100k_base

MAX_TOKENS_FOR_CHUNK = 500

DEFAULT_OVERLAP_TOKENS_FOR_CHUNK = 75

DEFAULT_EMBEDDING_DIMENTIONS = os.environ.get("DEFAULT_EMBEDDING_DIMENTIONS")

DEFAULT_TOP_K_RETRIEVE_SIZE = 8

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "jinaai/jina-reranker-v2-base-multilingual")