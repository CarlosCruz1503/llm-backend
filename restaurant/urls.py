from rest_framework.routers import DefaultRouter

from .views import MenuCategoryViewSet, MenuItemViewSet, ReservationViewSet, RestaurantTableViewSet, RestaurantViewSet

router = DefaultRouter()

router.register("restaurant", RestaurantViewSet, basename="restaurant")
router.register("table", RestaurantTableViewSet, basename="table")
router.register("menu-category", MenuCategoryViewSet, basename="menu-category")
router.register("menu-item", MenuItemViewSet, basename="menu-item")
router.register("reservation", ReservationViewSet, basename="reservation")

urlpatterns = router.urls
