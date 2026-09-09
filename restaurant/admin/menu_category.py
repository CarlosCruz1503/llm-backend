from django.contrib import admin

from restaurant.models import MenuCategory


class MenuCategoryAdmin(admin.ModelAdmin):
    pass


admin.site.register(MenuCategory, MenuCategoryAdmin)
