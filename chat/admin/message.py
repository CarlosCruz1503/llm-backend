from django.contrib import admin

from chat.models import Message

class MessageAdmin(admin.ModelAdmin):
    pass

admin.site.register(Message, MessageAdmin)