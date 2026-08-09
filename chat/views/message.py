from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from ..models import Message
from ..serializers import MessageSerializer


class MessageViewSet(ModelViewSet):
    """
    Message view set.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    # See ConversationViewSet.get_queryset for why this needs to be a method,
    # not just this class attribute: a class attribute is only evaluated
    # once, at import time, before ObjectsManager has a request/user to
    # scope by.
    queryset = Message.objects.all()

    def get_queryset(self):
        return Message.objects.all()
