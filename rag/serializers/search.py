import logging

from myapp.serializers.base import BaseSerializer
from rag.models.search import SearchModel
from rag.services.search import SearchService

logger = logging.getLogger(__name__)


class SearchSerializer(BaseSerializer):

    class Meta:
        model = SearchModel
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Define the single field allowed for input
        input_field = ['text', 'provider']

        # Dynamically mark every other field as read_only
        for field_name in self.fields:
            if field_name not in input_field:
                self.fields[field_name].read_only = True

    def create(self, validated_data):
        search_instance = SearchModel.objects.create(**validated_data)

        try:
            search_service = SearchService()
            return search_service.execute(search_instance)
        except Exception:
            # SearchService already records the failure on `search_instance.error`
            # and saves it before re-raising, so the client still gets a valid
            # record back (with the error visible in the response) instead of a
            # 500 caused by returning a bare dict from a ModelSerializer.create().
            logger.exception("Failed to execute search")
            return search_instance
