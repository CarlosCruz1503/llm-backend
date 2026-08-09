import logging
from types import SimpleNamespace

from chat.models.message import Message
from prompting.utils.structured_outputs.chat.message import messageOutputModel

from ..factory.output import promptsFactory
from ..factory.provider import factoryProvider

logger = logging.getLogger(__name__)


def create_client_for_prompt(validated_data):
    try:
        client = factoryProvider(validated_data["provider"])
        output_type = promptsFactory(validated_data["output_type"])
        return client(
            thinking_level=validated_data["thinking_level"],
            output_type=output_type,
            input=validated_data["input"],
        )
    except Exception:
        logger.exception("Failed to build the provider client for a prompt")
        raise


def create_client_for_message(validated_data, conversation):
    try:
        client = factoryProvider(validated_data["provider"])
        output_type_object = SimpleNamespace(structured_output=messageOutputModel)

        return client(
            thinking_level=validated_data["thinking_level"],
            input=validated_data["content"],
            output_type=output_type_object,
            conversation=conversation,
        )
    except Exception:
        logger.exception("Failed to build the provider client for a chat message")
        raise


def save_client_reponse_for_prompt(response, prompt):
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
    except Exception:
        logger.exception("Failed to map the provider response onto the prompt")
        raise


def save_client_reponse_for_message(sent_message, response):
    try:
        sent_message.tokens = response["input_tokens"]
        sent_message.request_id = response["id"]
        sent_message.status = response["status"]
        sent_message.response_code = response["response_code"]
        data = {
            "conversation": sent_message.conversation,
            "content": response["output"],
            "role": "assistant",
            "provider": sent_message.provider,
            "thinking_level": sent_message.thinking_level,
            "request_id": response["id"],
            "status": response["status"],
            "response_code": 200,
            "tokens": response["output_tokens"],
            "error": None,
        }
        received_message = Message.objects.create(**data)
        sent_message.save()
        return received_message
    except Exception:
        logger.exception("Failed to save the assistant's reply message")
        raise