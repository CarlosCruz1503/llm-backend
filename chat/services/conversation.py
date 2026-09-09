import logging

from chat.models.conversation import Conversation
from chat.models.message import Message
from agents.services.client import create_client_for_message, save_client_reponse_for_message

logger = logging.getLogger(__name__)


class ConversationService:

    def execute(self, validated_data):
        try:
            conversation = self.get_create_conversation(validated_data)
            sent_message = self.create_sent_message(validated_data, conversation)
            return self.execute_and_save_message_response(validated_data, sent_message)
        except Exception:
            logger.exception("Failed to process incoming chat message")
            raise
    
    def get_create_conversation(self, validated_data)-> Conversation:
        conversation = validated_data.get("conversation", None)
        if not conversation:
            conversation = Conversation.objects.create(
                title = validated_data["content"]
            )
            
        return conversation
    
    def create_sent_message(self,validated_data, conversation) -> Message: 
        validated_data["conversation"] = conversation
        return Message.objects.create(**validated_data)
    
    def execute_and_save_message_response(self, validated_data, sent_message):
        try:
            client = create_client_for_message(validated_data, sent_message.conversation)
            message_response = client.execute(is_chat=True)
            return save_client_reponse_for_message(sent_message, message_response)
        except Exception as e:
            logger.exception("Failed to get a response from the LLM provider")
            sent_message.error = f"Error: {e}"
            sent_message.save()
            raise