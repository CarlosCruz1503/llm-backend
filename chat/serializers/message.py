from rest_framework import serializers

from chat.models.conversation import Conversation
from chat.services.conversation import ConversationService
from myapp.serializers.base import BaseSerializer
from prompting.constants import DEFAULT_THINKING_LEVEL, ProviderChoices, ThinkingLevelChoices

from ..models import Message


class MessageSerializer(BaseSerializer):
    """
    Message serializer.
    """
    # NOTE: the `queryset=` used for validating this PK is set fresh on each
    # instance in __init__, not here. `Conversation.objects.all()` evaluated
    # in the class body would run exactly once, at import time, before
    # ObjectsManager has any request/user to scope by — freezing the
    # "allowed" conversations as *every* non-deleted conversation of *every*
    # user, forever. That would let any authenticated user attach a new
    # message to someone else's conversation id, and get that conversation's
    # history (and any LLM reply built from it) back in the response.
    conversation = serializers.PrimaryKeyRelatedField(
        queryset=Conversation.objects.none(),
        required=False,
        allow_null=True  # Optional: allows passing null if needed
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Evaluated per-instance (i.e. per-request), so ObjectsManager
        # correctly scopes this to the current user.
        self.fields["conversation"].queryset = Conversation.objects.all()
    # These are redeclared (rather than left to ModelSerializer's
    # auto-generation) for two reasons:
    #  1. Even though the model field has `choices`/`default`, DRF's
    #     ModelSerializer only turns that into `required=False` — it does
    #     NOT backfill the default into `validated_data` when the client
    #     omits the field. `ConversationService`/`create_client_for_message`
    #     read these straight out of validated_data, so omitting either
    #     field from a request used to raise a KeyError/500.
    #  2. An explicit `default=` on the serializer field makes DRF inject
    #     that default into validated_data, closing that gap, while
    #     ChoiceField still enforces the same choices as the model.
    thinking_level = serializers.ChoiceField(choices=ThinkingLevelChoices.choices, default=DEFAULT_THINKING_LEVEL)
    provider = serializers.ChoiceField(choices=ProviderChoices.choices, default=ProviderChoices.GEMINI)

    class Meta:
        model = Message
        fields = "__all__"
        # These are populated by the backend after calling the LLM provider,
        # never by the client — without this, a POST could set a message's
        # status/tokens/error directly, or fake an "assistant" role reply.
        read_only_fields = [
            "role", "model", "response_code", "status",
            "request_id", "tokens", "error",
        ]

    def create(self, validated_data):
        conversation_service = ConversationService()
        return conversation_service.execute(validated_data)
