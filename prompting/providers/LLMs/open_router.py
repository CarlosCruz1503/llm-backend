import json
import logging
from typing import Dict

from django.core.exceptions import ImproperlyConfigured
from openrouter import OpenRouter

from ...constants import OPENROUTER_API_KEY, OPENROUTER_MODEL, SYSTEM_INSTRUCTION_FOR_CHAT
from ..base import ChatProvider

logger = logging.getLogger(__name__)
class OpenRouterProvider(ChatProvider):

    model: str = OPENROUTER_MODEL

    def __init__(self, thinking_level, input, output_type, conversation=None):
        super().__init__(thinking_level, input, output_type, conversation)
        if not self.model or not OPENROUTER_API_KEY:
            raise ImproperlyConfigured(
                "OPENROUTER_MODEL / OPENROUTER_API_KEY environment variables are not set; "
                "the OpenRouter provider cannot run."
            )

    def build_message(self, is_chat):
        message = [
            {"role": "user", "content": self.input},
        ]
        if not is_chat:
            message.append({"role": "system", "content": self.output_type.prompt})
        return message

    def build_context(self, is_chat):
        message = self.build_message(is_chat)

        if not is_chat:
            return message

        history = self.retrieve_chat_history(self.conversation)
        system_message = [{"role": "system", "content": SYSTEM_INSTRUCTION_FOR_CHAT}]
        return [*system_message, *history, *message]

    def execute(self, is_chat=False):
        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "output_format",
                    "schema": self.output_type.structured_output.model_json_schema()
                }
            }
            with OpenRouter(api_key=OPENROUTER_API_KEY) as open_router:
                response = open_router.chat.send(
                    model=self.model,
                    messages=self.build_context(is_chat),
                    response_format=response_format
                )
            return self.transform_response(response)
        except Exception:
            logger.exception("OpenRouter provider execution failed")
            raise

    def transform_response(self, response) -> Dict:
        try:
            output_dict = json.loads(response.choices[0].message.content)
            self.validate_response(output_dict)
            return {
                'model': response.model,
                'output': output_dict["text"],
                'output_dict': output_dict,
                'id': response.id,
                'status': "Completed",
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
                'response_code': 200,
                'error': None,
            }
        except Exception:
            logger.exception("Failed to parse OpenRouter response")
            raise

    def format_chat_history(self, history: list) -> list:
        return [
            {
                "role": message.role,
                "content": [{"type": "text", "text": message.content}]
            }
            for message in history
        ]
