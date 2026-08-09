from django.contrib.auth.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        # Explicit allow-list: "__all__" would also serialize `password`
        # (the hash) and permission flags like `is_superuser`.
        fields = ["id", "username", "email", "first_name", "last_name"]