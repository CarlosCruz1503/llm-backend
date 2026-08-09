from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from ..models import Conversation
from ..serializers import ConversationSerializer


class ConversationViewSet(ModelViewSet):
    """
    Conversation view set.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    # `queryset` below is a class attribute evaluated once, at import time
    # (server startup) — before any request/user exists. DRF's default
    # get_queryset() just calls `.all()` on that already-built QuerySet,
    # which does NOT re-invoke ObjectsManager.get_queryset(), so the
    # per-request user-scoping it does would never actually run. Overriding
    # get_queryset() forces a fresh `Conversation.objects.all()` call (and
    # therefore a fresh manager evaluation) on every request.
    queryset = Conversation.objects.all()

    def get_queryset(self):
        return Conversation.objects.all()
