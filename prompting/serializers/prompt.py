import logging

from myapp.serializers.base import BaseSerializer

from agents.services.client import create_client_for_prompt, save_client_reponse_for_prompt

from ..models import PromptModel

logger = logging.getLogger(__name__)


class PromptSerializers(BaseSerializer):

    class Meta:
        model = PromptModel
        fields = "__all__"
        extra_kwargs = {
            'input': {'required': True, 'allow_null': False},
            'output_type': {'required': True, 'allow_null': False},
            'provider': {'required': True, 'allow_null': False},
            'thinking_level': {'required': True, 'allow_null': False}
        }
        # Populated by the backend after calling the LLM provider, never by
        # the client (mass-assignment guard, same reasoning as MessageSerializer).
        read_only_fields = [
            "output", "output_dict", "error", "response_code", "status",
            "request_id", "model", "input_tokens", "output_tokens", "total_tokens",
        ]

    def create(self, validated_data):
        prompt = PromptModel.objects.create(**validated_data)

        try:
            client = create_client_for_prompt(validated_data)
            response = client.execute()
            prompt = save_client_reponse_for_prompt(response, prompt)
        except Exception as e:
            logger.exception("Failed to get a response from the LLM provider")
            prompt.error = f"Error: {e}"

        prompt.save()

        return prompt