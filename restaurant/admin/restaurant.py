from django.contrib import admin

from restaurant.models import Restaurant


class RestaurantAdmin(admin.ModelAdmin):
    pass


admin.site.register(Restaurant, RestaurantAdmin)
