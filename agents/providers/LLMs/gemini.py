import json
import logging
import time
from typing import Any, Dict

from django.core.exceptions import ImproperlyConfigured
from google import genai
from google.genai import types


from agents.constants import AGENT_RESTAURANT_DEFAULT_INPUT
from myapp.constants import DEFAULT_EMBEDDING_DIMENTIONS, GEMINI_EMBEDDING_MODEL, GEMINI_MODEL, SYSTEM_INSTRUCTION_FOR_CHAT
from ..base import ChatProvider, EmbeddingsProvider

logger = logging.getLogger(__name__)


class GeminiProvider(ChatProvider, EmbeddingsProvider):

    model: str = GEMINI_MODEL
    embedding_model = GEMINI_EMBEDDING_MODEL
    client: Any
    function_call_responses:list = []

    def __init__(self, input, thinking_level="", output_type="", conversation=None, top_k=None, available_tools=None ):
        super().__init__(input,thinking_level, output_type, conversation,top_k, available_tools)
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
            call_response = self.format_chat_call_responses(self.function_call_responses)
            return [*history, *message, *call_response]
        
        if is_search:
            search = self.build_search_content()
            return search
        
        return message
    
    def execute(self, is_chat=False, is_search=False, retry=0):
        try:
        
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.build_context(is_chat, is_search),
                config=types.GenerateContentConfig(
                    tools=self.available_tools.get_tools_schemas(),
                    response_mime_type='application/json',
                    response_json_schema=self.output_type.structured_output.model_json_schema(),
                    system_instruction=AGENT_RESTAURANT_DEFAULT_INPUT
                )
            )
            if not is_chat:
                return self.transform_response(response)
            return self.transform_agent_response(response)
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
                # return self.execute(is_chat, is_search, retry=retry + 1)

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
        
    def format_chat_call_responses(self, call_responses: list) -> list:
        return [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=response["name"],
                            response={"result": response["result_data"]},
                        )
                    )
                ]
            )
            for response in call_responses
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
        
    def transform_agent_response(self, response):
        try:
            print(json.dumps(response.model_dump(mode="json"), indent=2, ensure_ascii=False))
        except Exception:
            # Never let a debug print take down the request.
            print(response)

        output = json.loads(response.text)

        function_results = []
        for step in output.get("function_calls", []):
            print(f"Function to call: {step['function_name']}")
            print(f"Arguments: {step['arguments']}")
            function_execution = self.available_tools.tools_execution(step["function_name"], step["arguments"])
            function_results.append({
                "type": "function_result",
                "name": step['function_name'],
                "result_data": json.dumps(function_execution),
            })

        if function_results:
            self.function_call_responses = [*self.function_call_responses,*function_results]
            print("Enviando resultados de la función al agente", function_results)
            time.sleep(90)
            print("Fin de sleep")
            return self.execute(is_chat=True)

        return {
            'model': response.model_version,
            'output': output.get("text") or "",
            'output_dict': output,
            'id': response.response_id,
            'status': "Completed",
            'response_code': 200,
            'input_tokens': response.usage_metadata.prompt_token_count,
            'output_tokens': response.usage_metadata.total_token_count - response.usage_metadata.prompt_token_count,
            'total_tokens': response.usage_metadata.total_token_count,
            'error': None,
            }
        
        
        
        
        
    def execute_agent_run(self):
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"{self.input}",
            config=types.GenerateContentConfig(
                tools=self.available_tools.get_tools_schemas(),
                response_mime_type='application/json',
                response_json_schema=self.output_type.structured_output.model_json_schema(),
                system_instruction=AGENT_RESTAURANT_DEFAULT_INPUT
            )
        )
        print("response", response)
        output_dict = json.loads(response.text)
        print("output_dict",output_dict)
        
        for step in output_dict["function_calls"]:
            print(f"Function to call: {step["function_name"]}")
            print(f"Arguments: {step["arguments"]}")
            print(self.available_tools.tools_execution(step["function_name"], step["arguments"]))
