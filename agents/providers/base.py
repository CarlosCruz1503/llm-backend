import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from chat.services.history import get_history_messages
from myapp.constants import MAX_TOKENS_FOR_CHAT_CONTEXTS

logger = logging.getLogger(__name__)


class Provider(ABC):

    input: str
    thinking_level: str
    output_type: str
    conversation: int = None
    top_k: list = None
    available_tools: list = None
    client: Any

    def __init__(self, input, thinking_level="", output_type="", conversation=None, top_k=None, available_tools=None):
        self.thinking_level = thinking_level
        self.input = input
        self.output_type = output_type
        self.conversation = conversation
        self.top_k = top_k
        self.available_tools = available_tools

    @abstractmethod
    def execute(self, is_chat=False):
        pass

    @abstractmethod
    def transform_response(self, response) -> Dict:
        pass

    @abstractmethod
    def build_message(self):
        pass

    @abstractmethod
    def build_context(self):
        pass

    def validate_response(self, response):
        """Validate the provider's JSON output against its expected pydantic
        schema, raising if it doesn't match. Returns the parsed model
        instance (callers currently use this only for the validation
        side-effect).
        """
        try:
            return self.output_type.structured_output.model_validate(response)
        except Exception:
            logger.exception("Provider response failed structured-output validation")
            raise


class ChatProvider(Provider):

    def retrieve_chat_history(self, conversation, max_tokens_context_allowed: int = MAX_TOKENS_FOR_CHAT_CONTEXTS) -> list:
        history = get_history_messages(conversation, max_tokens_context_allowed)
        return self.format_chat_history(history)

    @abstractmethod
    def format_chat_history(self, history: list) -> list:
        return []

class EmbeddingsProvider(Provider):
    
    def embed_content(self):
        pass