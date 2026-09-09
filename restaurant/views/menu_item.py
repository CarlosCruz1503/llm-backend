from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from ..models import MenuItem
from ..serializers import MenuItemSerializer


class MenuItemViewSet(ModelViewSet):
    """
    Menu item view set.
    """
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    queryset = MenuItem.objects.all()
