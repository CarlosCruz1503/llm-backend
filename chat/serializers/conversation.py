from rest_framework import serializers

from chat.serializers.message import MessageSerializer

from ..models import Conversation


class ConversationSerializer(serializers.ModelSerializer):
    """
    Conversation serializer.
    """

    # read_only: this is a nested reverse relation for display purposes.
    # ModelSerializer.create()/update() can't handle writable nested
    # serializers on their own, so leaving this writable made POST/PATCH on
    # /api/conversation/ effectively broken.
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = "__all__"