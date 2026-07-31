
from typing import Any, Dict
from ..base import Provider
from google import genai
from ...constants import MODEL_GEMINI
import json
class GeminiProvider(Provider):
    
    model: str = MODEL_GEMINI
    client: Any
    
    def __init__(self, thinking_level, output_type, input ):
        super().__init__(thinking_level, output_type, input )
        self.client = genai.Client()
        
    
    def execute(self):
        try:
            response = self.client.interactions.create(
                model=self.model,
                generation_config={
                    "thinking_level": self.thinking_level
                },
                system_instruction=self.output_type.prompt,
                input=self.input,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema":self.output_type.structured_output.model_json_schema()
                }
            )
            print(response)
            return self.transform_response(response)
        except Exception as e: 
            import traceback
            traceback.print_exc()
            print(f"Error {e}")
            raise
    
    def transform_response(self, response) -> Dict:
        try: 
            output_dict = json.loads(response.output_text)
            self.validate_response(output_dict)
            return {
                'model': response.model,
                'output': output_dict["text"],
                'output_dict':output_dict,
                'id':response.id,
                'status':response.status,
                'response_code':200,
                'input_tokens':response.usage.total_input_tokens,
                'output_tokens':response.usage.total_output_tokens,
                'total_tokens':response.usage.total_tokens,
                'error': None,
            }
        except Exception as e: 
            print(f"Error {e}")
            raise
        