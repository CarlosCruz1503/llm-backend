from django.contrib import admin

from restaurant.models import RestaurantTable


class RestaurantTableAdmin(admin.ModelAdmin):
    pass


admin.site.register(RestaurantTable, RestaurantTableAdmin)
