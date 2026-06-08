from django.contrib import admin
from .models import BodyMeasurement


@admin.register(BodyMeasurement)
class BodyMeasurementAdmin(admin.ModelAdmin):
    list_display = ('measured_at', 'weight_jin', 'bmi', 'body_fat_pct', 'body_age', 'heart_rate')
    list_filter = ('measured_at',)
    ordering = ('-measured_at',)
