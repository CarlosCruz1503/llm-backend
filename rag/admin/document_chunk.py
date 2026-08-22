from prompting.constants import ADMIN_LIST_DISPLAY
from rag.models import DocumentChunkModel
from django.contrib import admin

class DocumentChunkAdmin(admin.ModelAdmin):
    
    list_display = ('sequence', 'document', 'embedding') + ADMIN_LIST_DISPLAY
    pass

admin.site.register(DocumentChunkModel, DocumentChunkAdmin)