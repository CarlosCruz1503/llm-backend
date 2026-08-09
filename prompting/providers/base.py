import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from chat.services.history import get_history_messages
from prompting.constants import MAX_TOKENS_FOR_CHAT_CONTEXTS

logger = logging.getLogger(__name__)


class Provider(ABC):

    thinking_level: str
    output_type: str
    input: str
    conversation: int = None
    client: Any

    def __init__(self, thinking_level, input, output_type, conversation=None):
        self.thinking_level = thinking_level
        self.input = input
        self.output_type = output_type
        self.conversation = conversation

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
