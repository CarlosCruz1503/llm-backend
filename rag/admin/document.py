from django.contrib import admin

from rag.models.document import DocumentModel

class DocumentAdmin(admin.ModelAdmin):
    pass

admin.site.register(DocumentModel, DocumentAdmin)