

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class Provider(ABC):
    
    thinking_level: str
    output_type: str 
    input: str
    
    client: Any
    
    def __init__(self, thinking_level, output_type, input ):
        self.thinking_level = thinking_level
        self.output_type = output_type
        self.input = input
    @abstractmethod
    def execute(self):
        pass
    
    @abstractmethod
    def transform_response(self, response) -> Dict:
        pass
    
    def validate_response(self, response) -> bool:
        try:
            validated = self.output_type.structured_output.model_validate(response)
            print("Correct validation of the response")
            return validated
        except Exception as e:
            print(f"Error validating the structured output model: {e}")
            raise

