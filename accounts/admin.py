from django.contrib import admin
from .models import UserProfile, Post, Comment, BodyMeasurement


@admin.register(BodyMeasurement)
class BodyMeasurementAdmin(admin.ModelAdmin):
    list_display = ('measured_at', 'weight_jin', 'bmi', 'body_fat_pct', 'body_age', 'heart_rate')
    list_filter = ('measured_at',)
    ordering = ('-measured_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'last_login_ip', 'last_login_location')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'updated_at')
    list_filter = ('created_at', 'author')
    search_fields = ('title', 'content')
    ordering = ('-created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'content_preview', 'has_audio', 'created_at')
    list_filter = ('created_at', 'author')
    search_fields = ('content', 'author__username')

    @admin.display(description='Content')
    def content_preview(self, obj):
        return (obj.content[:50] + '…') if len(obj.content) > 50 else obj.content
