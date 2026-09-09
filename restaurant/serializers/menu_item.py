from myapp.serializers.base import BaseSerializer

from ..models import MenuItem


class MenuItemSerializer(BaseSerializer):
    """
    Menu item serializer.
    """

    class Meta:
        model = MenuItem
        fields = "__all__"
        read_only_fields = ["deleted"]
