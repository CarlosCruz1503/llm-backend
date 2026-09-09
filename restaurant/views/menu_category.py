from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from ..models import MenuCategory
from ..serializers import MenuCategorySerializer


class MenuCategoryViewSet(ModelViewSet):
    """
    Menu category view set.
    """
    serializer_class = MenuCategorySerializer
    permission_classes = [IsAuthenticated]
    queryset = MenuCategory.objects.all()
