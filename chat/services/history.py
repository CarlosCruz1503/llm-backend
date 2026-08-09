import logging

from django.db.models import F, Sum, Window

from chat.models.conversation import Conversation
from chat.models.message import Message

logger = logging.getLogger(__name__)


def get_history_messages(conversation: Conversation, max_tokens_context_allowed: int) -> list:
    """Return this conversation's messages that fit within the token budget,
    in chronological order (oldest first) as the LLM APIs expect.
    """
    # Window(order_by=...) only controls how the running `sum` is computed;
    # it doesn't change the queryset's own iteration order, which still
    # follows Message.Meta.ordering (newest first). We rely on that
    # descending order to walk backwards from the most recent message and
    # cut off once the running token count exceeds the budget.
    tokens_with_sum = Message.objects.filter(conversation=conversation).exclude(tokens__isnull=True).annotate(
        sum=Window(expression=Sum("tokens"), order_by=F("created_at").desc())
    )

    history_messages = [
        log for log in tokens_with_sum
        if (int(log.sum) - int(log.tokens)) <= max_tokens_context_allowed
    ]

    # The list above is still newest-first; reverse it so the LLM receives
    # the conversation in the order it actually happened.
    history_messages.reverse()
    return history_messages
