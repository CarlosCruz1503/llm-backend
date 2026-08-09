from rest_framework.routers import DefaultRouter

from .views import PromptView

router = DefaultRouter()
router.register("prompt", PromptView, basename="prompt")

urlpatterns = router.urls
