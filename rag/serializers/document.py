from myapp.serializers.base import BaseSerializer
from rag.models.document import DocumentModel
from rag.tasks import task_process_document


class DocumentSerializer(BaseSerializer):

    class Meta:
        model = DocumentModel
        fields = "__all__"
        read_only_fields = [
            "file_name", "file_size", "page_size", "deleted", "text_content", "text_extracted", "error", "status"
        ]

    def extract_metadata(self, validated_data):
        validated_data["file_name"] = validated_data["file"].name
        validated_data["file_size"] = validated_data["file"].size
        return True
    
    def create(self, validated_data):
        # DocumentService.process_document always returns a saved DocumentModel,
        # recording any failure on `document.error` instead of raising, so the
        # client gets a valid record back (with the error visible in the
        # response) instead of a 500 caused by returning a bare dict from a
        # ModelSerializer.create().
        self.extract_metadata(validated_data)
        document = DocumentModel.objects.create(**validated_data)

        # Optional chunking overrides (used by the RAG evaluation experiments
        # to run different chunk_size/chunk_overlap/token_model configurations).
        # Regular API callers never set this context, so normal requests keep
        # using the env-backed defaults untouched.
        chunk_config = self.context.get("chunk_config") or {}
        task_process_document.delay(
            document.id,
            chunk_model=chunk_config.get("model"),
            chunk_size=chunk_config.get("chunk_size"),
            chunk_overlap=chunk_config.get("chunk_overlap"),
        )
        return document
