from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    """Base serializer for models inheriting from BaseModel.

    ``user`` is read-only: it's assigned automatically in BaseModel.save()
    from the authenticated request, never from client input. Without this,
    a client could pass any ``user`` id in the payload and create/attribute
    records to a different account (mass assignment / IDOR).
    """

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        read_only_fields = [
            "deleted"
        ]