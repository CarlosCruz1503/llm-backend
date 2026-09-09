from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from ..models import RestaurantTable
from ..serializers import RestaurantTableSerializer


class RestaurantTableViewSet(ModelViewSet):
    """
    Restaurant table view set.
    """
    serializer_class = RestaurantTableSerializer
    permission_classes = [IsAuthenticated]
    queryset = RestaurantTable.objects.all()
