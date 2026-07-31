from ..providers.LLMs import GeminiProvider, OpenRouterProvider

models = {
    # "claude": ClaudeProvider,   # not implemented yet, see providers/LLMs/claude.py
    "gemini": GeminiProvider,
    # "openai": OpenAIProvider,   # not implemented yet, see providers/LLMs/open_ai.py
    "openrouter": OpenRouterProvider
}

def factoryProvider(provider: str):

    model_class = models.get(provider)
    if model_class is None:
        raise NotImplementedError(f"Provider '{provider}' is not implemented yet")

    return model_class