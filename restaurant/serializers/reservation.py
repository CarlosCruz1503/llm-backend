from myapp.serializers.base import BaseSerializer

from ..models import Reservation


class ReservationSerializer(BaseSerializer):
    """
    Reservation serializer.
    """

    class Meta:
        model = Reservation
        fields = "__all__"
        read_only_fields = ["deleted"]
