import json
import logging
from typing import Any, Dict

from django.core.exceptions import ImproperlyConfigured
from google import genai
from google.genai import types

from ...constants import MODEL_GEMINI, SYSTEM_INSTRUCTION_FOR_CHAT
from ..base import ChatProvider

logger = logging.getLogger(__name__)


class GeminiProvider(ChatProvider):

    model: str = MODEL_GEMINI
    client: Any

    def __init__(self, thinking_level, input, output_type, conversation=None):
        super().__init__(thinking_level, input, output_type, conversation)
        if not self.model:
            raise ImproperlyConfigured(
                "GEMINI_AI_MODEL environment variable is not set; the Gemini provider cannot run."
            )
        self.client = genai.Client()

    def build_message(self, is_chat):
        message = [types.Content(
            role='user',
            parts=[types.Part(text=f"{self.input}")]
        )]
        if not is_chat:
            message.append(types.Content(
                role='user',
                parts=[types.Part(text=f"{self.output_type.prompt}")]
            ))
        return message

    def build_context(self, is_chat):
        message = self.build_message(is_chat)

        if not is_chat:
            return message

        history = self.retrieve_chat_history(self.conversation)
        return [*history, *message]

    def execute(self, is_chat=False):
        try:
            config = {
                'response_mime_type': 'application/json',
                'response_schema': self.output_type.structured_output.model_json_schema(),
            }
            if is_chat:
                # Gemini takes the system prompt out-of-band via config,
                # rather than as another message in `contents`.
                config['system_instruction'] = SYSTEM_INSTRUCTION_FOR_CHAT

            response = self.client.models.generate_content(
                model=self.model,
                contents=self.build_context(is_chat),
                config=config,
            )
            return self.transform_response(response)
        except Exception:
            logger.exception("Gemini provider execution failed")
            raise

    def transform_response(self, response) -> Dict:
        try:
            output_dict = json.loads(response.text)
            self.validate_response(output_dict)
            return {
                'model': response.model_version,
                'output': output_dict["text"],
                'output_dict': output_dict,
                'id': response.response_id,
                'status': "Completed",
                'response_code': 200,
                'input_tokens': response.usage_metadata.prompt_token_count,
                'output_tokens': response.usage_metadata.total_token_count - response.usage_metadata.prompt_token_count,
                'total_tokens': response.usage_metadata.total_token_count,
                'error': None,
            }
        except Exception:
            logger.exception("Failed to parse Gemini response")
            raise

    def format_chat_history(self, history: list) -> list:
        return [
            types.Content(
                role='model' if message.role == 'assistant' else 'user',
                parts=[types.Part(text=message.content)]
            )
            for message in history
        ]
