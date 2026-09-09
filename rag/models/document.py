from django.db import models

from myapp.base.models import BaseModel
from myapp.constants import ProviderChoices
from rag.constants import DEFAULT_DOCUMENT_STATUS, DocumentStatusChoices

class DocumentModel(BaseModel):

    file = models.FileField(verbose_name="document file",upload_to="documents/")
    file_name = models.CharField(max_length=255, null=False, blank=False)
    file_size = models.FloatField(help_text="file size in Bytes", null=False, blank=False)
    page_size = models.FloatField(help_text="Number of pages in case of PDF", null=True, blank=True)
    text_content = models.TextField(null=True, blank=True)
    text_extracted = models.BooleanField(default=False)
    error = models.CharField(null=True, blank=True)
    provider = models.CharField(choices=ProviderChoices.choices, default=ProviderChoices.GEMINI)
    status = models.CharField(
        choices=DocumentStatusChoices.choices,
        default=DEFAULT_DOCUMENT_STATUS,
        help_text="Where this document is in the async extract/chunk/embed pipeline",
    )
