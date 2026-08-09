

from random import choices
from myapp.base.models import BaseModel
from django.db import models

class DocumentModel(BaseModel):
    
    file = models.FileField(verbose_name="document file",upload_to="documents/")
    file_name = models.CharField(max_length=255, null=False, blank=False)
    file_size = models.FloatField(help_text="file size in Bytes", null=False, blank=False)
    number_of_pages = models.FloatField(help_text="Number of pages in case of PDF", null=True, blank=True)
    
    