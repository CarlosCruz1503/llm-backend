from myapp.serializers.base import BaseSerializer

from ..models import RestaurantTable


class RestaurantTableSerializer(BaseSerializer):
    """
    Restaurant table serializer.
    """

    class Meta:
        model = RestaurantTable
        fields = "__all__"
        read_only_fields = ["deleted"]
