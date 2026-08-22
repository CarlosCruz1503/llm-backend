


from django.db import models
from myapp.base.models import BaseModel
from prompting.constants import DEFAULT_EMBEDDING_DIMENTIONS, ProviderChoices, TokenModelChoices
from rag.models.document import DocumentModel
from pgvector.django import VectorField
from pgvector.django import HnswIndex
class DocumentChunkModel(BaseModel):
    
    provider = models.CharField(choices=ProviderChoices.choices, default=ProviderChoices.GEMINI)
    document = models.ForeignKey(DocumentModel, null=False, on_delete=models.CASCADE)
    text = models.TextField(null=False)
    sequence = models.IntegerField(null=False)
    token_model = models.CharField(choices=TokenModelChoices, null=False)
    token_size = models.CharField(help_text="chunk size in tokens", max_length=255 , null=False)
    token_overlap = models.CharField(help_text="chunk overlap in tokens",max_length=255,  null=False)
    embedding = VectorField(
        dimensions=int(DEFAULT_EMBEDDING_DIMENTIONS),
        help_text="Vector embeddings of the text content",
        null=True,
        blank=True,
    )
    error_embedding = models.CharField(help_text="Error in embedding process", max_length=255 , null=True)
    
    class Meta:
        indexes = [
                HnswIndex(
                    name="embedding_vectors_index",
                    fields=["embedding"],
                    m=16,
                    ef_construction=64,
                    opclasses=["vector_cosine_ops"],
                )
            ]