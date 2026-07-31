from rest_framework import serializers
from ..models import PromptModel
from ..services.client import create_client, save_client_reponse

class PromptSerializers(serializers.ModelSerializer):
    
    class Meta:
        model = PromptModel
        fields = "__all__"
        extra_kwargs = {
            'input': {'required': True, 'allow_null': False},
            'output_type': {'required': True, 'allow_null': False},
            'provider': {'required': True, 'allow_null': False},
            'thinking_level': {'required': True, 'allow_null': False}
        }
    
    def create(self, validated_data):
        prompt = PromptModel.objects.create(**validated_data)

        try:
            client = create_client(validated_data)
            response = client.execute()
            prompt = save_client_reponse(response, prompt)
        except Exception as e:
            print(f"Error {e}")
            prompt.error = f"Error: {e}"

        prompt.save()

        return prompt