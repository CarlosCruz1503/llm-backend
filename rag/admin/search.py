from django.contrib import admin
from rag.models import SearchModel

class SearchAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'text', 'response','total_tokens','chunk_list', 'error')
    pass

admin.site.register(SearchModel, SearchAdmin)