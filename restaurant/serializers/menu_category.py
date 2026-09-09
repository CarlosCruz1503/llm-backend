from myapp.serializers.base import BaseSerializer

from ..models import MenuCategory


class MenuCategorySerializer(BaseSerializer):
    """
    Menu category serializer.
    """

    class Meta:
        model = MenuCategory
        fields = "__all__"
        read_only_fields = ["deleted"]
