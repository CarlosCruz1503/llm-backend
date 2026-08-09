from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import PromptModel
from ..serializers import PromptSerializers


class PromptView(viewsets.ModelViewSet):
    """
    PromptView.
    """
    serializer_class = PromptSerializers
    permission_classes = [IsAuthenticated]
    # See chat.views.conversation.ConversationViewSet.get_queryset: this
    # needs to be a method, not just a class attribute, so it's re-evaluated
    # (and re-scoped to the current user by ObjectsManager) on every request.
    queryset = PromptModel.objects.all()
