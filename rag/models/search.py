

from pgvector.django import HnswIndex, VectorField
from myapp.base.models import UserModel
from django.db import models
from myapp.constants import DEFAULT_EMBEDDING_DIMENTIONS, ProviderChoices
from rag.models.document_chunk import DocumentChunkModel
class SearchModel(UserModel):
    
    provider = models.CharField(choices=ProviderChoices.choices, default=ProviderChoices.GEMINI)
    text = models.TextField( blank=False, null=False)
    search_embedding = VectorField(
        dimensions=int(DEFAULT_EMBEDDING_DIMENTIONS),
        help_text="Vector embeddings of the search content",
        null=True,
        blank=True,
    )
    error = models.CharField(null=True, blank=True)
    response = models.TextField(blank=True, null=True)
    model = models.CharField(max_length=255, null=True, blank=True)
    response_code = models.CharField(max_length=128, null=True, blank=True)
    status = models.CharField(max_length=128, null=True, blank=True)
    request_id = models.CharField(max_length=128, null=True, blank=True)
    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    total_tokens = models.IntegerField(null=True, blank=True) 
    top_chunk = models.ForeignKey(DocumentChunkModel, on_delete=models.CASCADE, null=True, blank=True)
    distance_top_chunk = models.FloatField(null=True, blank=True) 
    
    chunk_list = models.JSONField(default=list)
    
    class Meta:
        indexes = [
                HnswIndex(
                    name="search_embedding_vectors_index",
                    fields=["search_embedding"],
                    m=16,
                    ef_construction=64,
                    opclasses=["vector_cosine_ops"],
                )
            ]