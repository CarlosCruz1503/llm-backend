import json
from ..factory.provider import factoryProvider
from ..factory.output import promptsFactory

def create_client(validated_data):
    try:
        client = factoryProvider(validated_data["provider"])
        output_type = promptsFactory(validated_data["output_type"])
        client_object = client(
            thinking_level= validated_data["thinking_level"],
            output_type=output_type,
            input = validated_data["input"],
        )
        
        return client_object
    except Exception as e: 
        print(f"Error {e}")
        raise

def save_client_reponse(response, prompt):
    
    try: 
        prompt.model = response["model"]      
        prompt.output = response["output"]
        prompt.output_dict = response["output_dict"]
        prompt.request_id = response["id"]
        prompt.status = response["status"]
        prompt.response_code = response["response_code"]
        prompt.input_tokens = response["input_tokens"]
        prompt.output_tokens = response["output_tokens"]
        prompt.total_tokens = response["total_tokens"]
        prompt.error = response["error"]
        return prompt
    except Exception as e:
        print(f"Error {e}")
        raise
