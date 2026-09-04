from django.contrib.auth.models import User
from django.test import TestCase

from chat.models.conversation import Conversation
from chat.models.message import Message
from chat.services.conversation import ConversationService
from chat.services.history import get_history_messages


class ChatTestCase(TestCase):
    """UserModel.save() (myapp/base/models.py) falls back to the first
    superuser when there's no request-bound current user (true for every
    test, since crum's current-user is only set inside the request/response
    cycle) — every Conversation/Message create in these tests needs one to
    exist, or the not-null `user` FK fails.
    """

    def setUp(self):
        User.objects.create_superuser(username="tester", email="tester@example.com", password="password123")


class GetHistoryMessagesTests(ChatTestCase):
    """get_history_messages (chat/services/history.py) is the token-budget
    window chat relies on to keep conversation history within a model's
    context limit — see README > Design decisions worth reading.
    """

    def _create_message(self, conversation, tokens):
        return Message.objects.create(conversation=conversation, content="x", tokens=tokens)

    def test_returns_every_message_when_under_budget(self):
        conversation = Conversation.objects.create(title="t")
        first = self._create_message(conversation, tokens=10)
        second = self._create_message(conversation, tokens=10)

        history = get_history_messages(conversation, max_tokens_context_allowed=100)

        # Chronological order (oldest first), as the LLM APIs expect.
        self.assertEqual([m.id for m in history], [first.id, second.id])

    def test_drops_oldest_messages_once_budget_is_exceeded(self):
        # A message is kept as long as the messages newer than it already
        # fit the budget on their own (see get_history_messages' docstring
        # on the running-sum-minus-self check) — so with a 70-token budget,
        # the two newest (40 + 40 = 80... but checked one at a time, 0 then
        # 40, both <= 70) are kept, while the oldest is dropped because the
        # 80 tokens already used by the two newer messages exceeds it.
        conversation = Conversation.objects.create(title="t")
        self._create_message(conversation, tokens=50)  # too old to fit
        kept = self._create_message(conversation, tokens=40)
        newest = self._create_message(conversation, tokens=40)

        history = get_history_messages(conversation, max_tokens_context_allowed=70)

        self.assertEqual([m.id for m in history], [kept.id, newest.id])

    def test_ignores_messages_with_no_token_count(self):
        # e.g. a message whose provider call failed before tokens were known.
        conversation = Conversation.objects.create(title="t")
        Message.objects.create(conversation=conversation, content="x", tokens=None)
        counted = self._create_message(conversation, tokens=10)

        history = get_history_messages(conversation, max_tokens_context_allowed=100)

        self.assertEqual([m.id for m in history], [counted.id])


class ConversationServiceTests(ChatTestCase):

    def test_get_create_conversation_creates_a_new_one_when_none_given(self):
        service = ConversationService()
        conversation = service.get_create_conversation({"content": "hello"})

        self.assertIsNotNone(conversation.pk)
        self.assertEqual(conversation.title, "hello")

    def test_get_create_conversation_reuses_the_given_one(self):
        existing = Conversation.objects.create(title="existing")
        service = ConversationService()

        conversation = service.get_create_conversation({"conversation": existing, "content": "hello"})

        self.assertEqual(conversation.pk, existing.pk)
