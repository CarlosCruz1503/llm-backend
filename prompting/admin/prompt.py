from django.contrib import admin
from ..models import PromptModel


class PromptModelAdmin(admin.ModelAdmin):
    pass


admin.site.register(PromptModel, PromptModelAdmin)