
from typing import Dict
from ..base import Provider
from ...constants import OPENROUTER_API_KEY, OPENROUTER_MODEL
from openrouter import OpenRouter
import json

class OpenRouterProvider(Provider):

    model: str = OPENROUTER_MODEL

    def execute(self):
        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "output_format",
                    "schema": self.output_type.structured_output.model_json_schema()
                }
            }
            with OpenRouter(
                api_key=OPENROUTER_API_KEY
            ) as open_router:
                response = open_router.chat.send(
                    model=self.model,
                    messages=[
                        { "role": "system", "content": self.output_type.prompt },
                        { "role": "user", "content": self.input },
                    ],
                    stream=False,
                    response_format=response_format
                )
                print("response:",response)
            return self.transform_response(response)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error in provider response: {e}")
            raise

    def transform_response(self, response) -> Dict:
        try:
            output_dict = json.loads(response.choices[0].message.content)
            self.validate_response(output_dict)
            return {
                'model': response.model,
                'output': output_dict["text"],
                'output_dict':output_dict,
                'id':response.id,
                'status':"Completed",
                'input_tokens':response.usage.prompt_tokens,
                'output_tokens':response.usage.completion_tokens,
                'total_tokens':response.usage.total_tokens,
                'response_code': 200,
                'error': None,
            }
        except Exception as e:
            print(f"Error {e}")
            raise