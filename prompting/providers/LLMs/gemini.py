import json
import logging
import time
from typing import Any, Dict

from django.core.exceptions import ImproperlyConfigured
from google import genai
from google.genai import types

from ...constants import DEFAULT_EMBEDDING_DIMENTIONS, GEMINI_EMBEDDING_MODEL, GEMINI_MODEL, SYSTEM_INSTRUCTION_FOR_CHAT
from ..base import ChatProvider, EmbeddingsProvider

logger = logging.getLogger(__name__)


class GeminiProvider(ChatProvider, EmbeddingsProvider):

    model: str = GEMINI_MODEL
    embedding_model = GEMINI_EMBEDDING_MODEL
    client: Any

    def __init__(self, input, thinking_level="", output_type="", conversation=None, top_k=None):
        super().__init__(input,thinking_level, output_type, conversation,top_k)
        if not self.model:
            raise ImproperlyConfigured(
                "GEMINI_AI_MODEL environment variable is not set; the Gemini provider cannot run."
            )
        self.client = genai.Client()

    def build_message(self, is_chat, is_search):
        message = [types.Content(
            role='user',
            parts=[types.Part(text=f"{self.input}")]
        )]
        if not is_chat and not is_search:
            message.append(types.Content(
                role='user',
                parts=[types.Part(text=f"{self.output_type.prompt}")]
            ))
        return message
    
    def build_search_content(self):
        
        return types.Content(
                role='user',
                parts=[types.Part(text=f'Answer the question or search {self.input} based on this top_k rag chunks {json.dumps(self.top_k, indent=2)}')]
            )
        

    def build_context(self, is_chat, is_search):
        message = self.build_message(is_chat, is_search)


        if is_chat:
            history = self.retrieve_chat_history(self.conversation)
            return [*history, *message]
        
        if is_search:
            search = self.build_search_content()
            return search
        
        return message
    def execute(self, is_chat=False, is_search=False, retry=0):
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
                contents=self.build_context(is_chat, is_search),
                config=config,
            )

            return self.transform_response(response)
        except Exception:
            max_retries = 3
            if retry < max_retries:
                logger.warning(
                    "Gemini provider execution failed (attempt %s/%s), retrying...",
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
            logger.exception("Gemini provider execution failed after %s attempts", max_retries + 1)
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

    def embed_content(self):
        try: 
            embedding_response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=self.input,
                config=types.EmbedContentConfig(output_dimensionality=DEFAULT_EMBEDDING_DIMENTIONS)
            )
            return embedding_response.embeddings[0].values
        except Exception:
            logger.exception("Failed to generate Gemini embedding")
            raise