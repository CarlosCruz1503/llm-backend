from django.contrib import admin

from chat.models import Conversation

class ConversationAdmin(admin.ModelAdmin):
    pass

admin.site.register(Conversation, ConversationAdmin)