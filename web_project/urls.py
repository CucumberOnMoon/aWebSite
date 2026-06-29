from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from accounts import views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('success/', views.success_view, name='success'),
    path('posts/', views.post_list, name='post_list'),
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    path('posts/create/', views.post_create, name='post_create'),
    path('users/', views.user_manage, name='user_manage'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('posts/<int:post_id>/translate/', views.translate_post, name='translate_post'),
    path('posts/<int:post_id>/transcribe/', views.transcribe_audio, name='transcribe_audio'),
    path('comments/received/', views.received_comments, name='received_comments'),
    path('weight-data/', views.weight_data, name='weight_data'),
    path('weight-data/upload/', views.weight_upload, name='weight_upload'),
    path('weight-data/delete/<int:pk>/', views.weight_delete, name='weight_delete'),
    path('fitness/', views.fitness_stats, name='fitness_stats'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
