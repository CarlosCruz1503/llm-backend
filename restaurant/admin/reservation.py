from django.contrib import admin

from restaurant.models import Reservation


class ReservationAdmin(admin.ModelAdmin):
    pass


admin.site.register(Reservation, ReservationAdmin)
