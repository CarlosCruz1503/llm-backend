from rest_framework.routers import DefaultRouter

from .views import ConversationViewSet, MessageViewSet

router = DefaultRouter()

router.register("conversation", ConversationViewSet, basename="conversation")
router.register("message", MessageViewSet, basename="message")

urlpatterns = router.urls
