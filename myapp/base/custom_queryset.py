from crum import get_current_user
from django.db import models

class ObjectsUserManager(models.Manager):
    """General object's manager to filter deleted rows and scope by owner."""

    def get_queryset(self):
        """Return the queryset without deleted objects, scoped to the
        current request's user so one user can never list/retrieve another
        user's rows (staff/superusers keep full visibility, e.g. in admin).
        """
        queryset = super().get_queryset().filter(deleted=False)
        user = get_current_user() 
        if user and user.is_authenticated and not user.is_staff:
            queryset = queryset.filter(user=user)
        return queryset