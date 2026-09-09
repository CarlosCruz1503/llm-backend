from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from ..models import Restaurant
from ..serializers import RestaurantSerializer


class RestaurantViewSet(ModelViewSet):
    """
    Restaurant view set.
    """
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated]
    queryset = Restaurant.objects.all()
