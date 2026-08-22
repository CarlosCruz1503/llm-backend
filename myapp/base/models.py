from django.db import models
from django.contrib.auth.models import User
from crum import get_current_user

from myapp.base.custom_queryset import ObjectsUserManager

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
class UserModel(BaseModel):
    """
    User model.
    """
    user = models.ForeignKey(User, on_delete=models.RESTRICT, null=False, blank=False)

    objects = ObjectsUserManager()

    def save(self, *args, **kwargs):
        # Only set on creation (when the object doesn't have a pk yet).
        # Without this check, every update (e.g. a PATCH by a different
        # user) would silently reassign ownership to whoever is logged in.
        if not self.pk:
            user = get_current_user()
            if user and user.is_authenticated:
                self.user = user

        super().save(*args, **kwargs)
        
    class Meta:
        abstract = True