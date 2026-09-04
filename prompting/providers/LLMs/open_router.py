import json
import logging
import time
from typing import Dict

from django.core.exceptions import ImproperlyConfigured
from openrouter import OpenRouter

from ...constants import DEFAULT_EMBEDDING_DIMENTIONS, OPENROUTER_API_KEY, OPENROUTER_EMBEDDING_MODEL, OPENROUTER_MODEL, SYSTEM_INSTRUCTION_FOR_CHAT
from ..base import ChatProvider

logger = logging.getLogger(__name__)
class OpenRouterProvider(ChatProvider):

    model: str = OPENROUTER_MODEL
    embedding_model = OPENROUTER_EMBEDDING_MODEL

    def __init__(self, input, thinking_level="", output_type="", conversation=None, top_k=None):
        super().__init__(input,thinking_level, output_type, conversation,top_k)
        if not self.model or not OPENROUTER_API_KEY:
            raise ImproperlyConfigured(
                "OPENROUTER_MODEL / OPENROUTER_API_KEY environment variables are not set; "
                "the OpenRouter provider cannot run."
            )

    def build_search_content(self):
        
        return [
            {"role": "user", 
             "content": f"Answer the question or search {self.input} based on this top_k rag chunks {json.dumps(self.top_k, indent=2)}"},
        ]
        
    def build_message(self, is_chat, is_search):
        message = [
            {"role": "user", "content": self.input},
        ]
        if not is_chat and not is_search:
            message.append({"role": "system", "content": self.output_type.prompt})
        return message

    def build_context(self, is_chat, is_search):
        message = self.build_message(is_chat, is_search)

        if is_chat:
            history = self.retrieve_chat_history(self.conversation)
            system_message = [{"role": "system", "content": SYSTEM_INSTRUCTION_FOR_CHAT}]
            return [*system_message, *history, *message]
        if is_search:
            return self.build_search_content()
            
        return message

        


    def execute(self, is_chat=False, is_search=False, retry=0):
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
                    messages=self.build_context(is_chat, is_search),
                    response_format=response_format
                )
            return self.transform_response(response)
        except Exception:
            max_retries = 3
            if retry < max_retries:
                logger.warning(
                    "OpenRouter provider execution failed (attempt %s/%s), retrying...",
                    retry + 1, max_retries + 1, exc_info=True,
                )
                # Backoff before retrying: on a free-tier quota/saturation
                # error, hitting the API again immediately just fails the
                # same way. Capped (rather than 10**retry, which reaches 100s
                # on the 3rd attempt) since this sleep blocks the caller's
                # thread directly — including, for prompt/chat/search, the
                # synchronous HTTP request itself.
                time.sleep(min(2 ** retry, 8))
                return self.execute(is_chat, is_search, retry=retry + 1)

            # Retries exhausted: log and re-raise so the caller (e.g.
            # SearchService/ChatService) sees a real exception instead of a
            # silently swallowed None — which would otherwise surface later
            # as a confusing, unrelated-looking failure further downstream.
            logger.exception("OpenRouter provider execution failed after %s attempts", max_retries + 1)
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

    def embed_content(self):
        try: 
            with OpenRouter(api_key=OPENROUTER_API_KEY) as open_router:
                response = open_router.embeddings.generate(
                    model=self.embedding_model,
                    input=self.input,
                    dimensions=DEFAULT_EMBEDDING_DIMENTIONS
                )
            
            return response.data[0].embedding
        except Exception:
            logger.exception("Failed to generate openrouter embedding")
            raise