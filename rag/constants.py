from django.db import models


class DocumentStatusChoices(models.TextChoices):
    """Lifecycle of a document through the async processing pipeline
    (see rag/tasks.py):

        PENDING -> EXTRACTING -> CHUNKING -> EMBEDDING -> COMPLETED
                        \\_____________________________/-> FAILED
    """
    PENDING = "pending", "Pending"
    EXTRACTING = "extracting", "Extracting text"
    CHUNKING = "chunking", "Chunking"
    EMBEDDING = "embedding", "Generating embeddings"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


DEFAULT_DOCUMENT_STATUS = DocumentStatusChoices.PENDING
