from django.test import SimpleTestCase

from prompting.factory.output import promptsFactory
from prompting.factory.provider import factoryProvider
from prompting.providers.LLMs.gemini import GeminiProvider
from prompting.providers.LLMs.open_router import OpenRouterProvider
from prompting.providers.base import Provider
from prompting.providers.prompts.text import PromptType
from prompting.schemas.prompt import SummarizeOutputModel, classifyOutputModel, keyWordsOutputModel


class ConcreteProvider(Provider):
    """Minimal concrete Provider used to exercise the base class's shared
    behavior (validate_response) without touching any real LLM SDK/client.
    """

    def execute(self, is_chat=False):
        pass

    def transform_response(self, response):
        pass

    def build_message(self):
        pass

    def build_context(self):
        pass


class FactoryProviderTests(SimpleTestCase):
    """factoryProvider is the one place every caller goes through to turn a
    provider name into a concrete class (see README > Provider abstraction);
    a mistake here would silently route every provider call to the wrong
    LLM, or to none at all.
    """

    def test_returns_gemini_provider(self):
        self.assertIs(factoryProvider("gemini"), GeminiProvider)

    def test_returns_openrouter_provider(self):
        self.assertIs(factoryProvider("openrouter"), OpenRouterProvider)

    def test_unknown_provider_raises(self):
        with self.assertRaises(NotImplementedError):
            factoryProvider("some-unregistered-provider")


class PromptsFactoryTests(SimpleTestCase):
    """promptsFactory backs the one-shot /api/prompt/ endpoint's
    output_type -> (system prompt, pydantic schema) lookup.
    """

    def test_summarize_maps_to_its_schema(self):
        prompt = promptsFactory(PromptType.SUMMARIZE)
        self.assertIs(prompt.structured_output, SummarizeOutputModel)
        self.assertTrue(prompt.prompt.strip())

    def test_classify_maps_to_its_schema(self):
        prompt = promptsFactory(PromptType.CLASSIFY)
        self.assertIs(prompt.structured_output, classifyOutputModel)

    def test_extract_keywords_maps_to_its_schema(self):
        prompt = promptsFactory(PromptType.EXTRACT_KEYWORDS)
        self.assertIs(prompt.structured_output, keyWordsOutputModel)

    def test_unknown_output_type_returns_none(self):
        # promptsFactory is a plain dict.get(), not a factory that raises on
        # a miss — callers relying on it should not assume a value comes back.
        self.assertIsNone(promptsFactory("not-a-real-output-type"))


class ProviderValidateResponseTests(SimpleTestCase):
    """Every provider's transform_response calls validate_response() before
    trusting a raw LLM response (see README > Design decisions worth
    reading). This is the contract every provider relies on holding.
    """

    def _provider_for(self, structured_output):
        provider = ConcreteProvider(input="irrelevant for this test")
        provider.output_type = type("OutputType", (), {"structured_output": structured_output})()
        return provider

    def test_valid_payload_passes(self):
        provider = self._provider_for(SummarizeOutputModel)
        validated = provider.validate_response({
            "text": "a short summary",
            "category": "Novel",
            "words_count": 4,
            "language": "en",
        })
        self.assertEqual(validated.words_count, 4)

    def test_invalid_payload_raises(self):
        provider = self._provider_for(SummarizeOutputModel)
        with self.assertRaises(Exception):
            # Missing required fields entirely.
            provider.validate_response({"text": "not enough fields"})
