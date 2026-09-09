from myapp.serializers.base import BaseSerializer

from ..models import Restaurant


class RestaurantSerializer(BaseSerializer):
    """
    Restaurant serializer.
    """

    class Meta:
        model = Restaurant
        fields = "__all__"
        read_only_fields = ["deleted"]
