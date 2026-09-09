from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from ..models import Reservation
from ..serializers import ReservationSerializer


class ReservationViewSet(ModelViewSet):
    """
    Reservation view set.
    """
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]
    # `queryset` below is a class attribute evaluated once, at import time
    # (server startup) — before any request/user exists. DRF's default
    # get_queryset() just calls `.all()` on that already-built QuerySet,
    # which does NOT re-invoke ObjectsUserManager.get_queryset(), so the
    # per-request user-scoping it does would never actually run. Overriding
    # get_queryset() forces a fresh `Reservation.objects.all()` call (and
    # therefore a fresh manager evaluation) on every request.
    queryset = Reservation.objects.all()

    def get_queryset(self):
        return Reservation.objects.all()
