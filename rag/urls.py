from rest_framework.routers import DefaultRouter

from rag.views.search import SearchViewSet
from .views import DocumentViewSet
router = DefaultRouter()
router.register("document", DocumentViewSet, basename="document")
router.register("search", SearchViewSet, basename="search" )
urlpatterns = router.urls