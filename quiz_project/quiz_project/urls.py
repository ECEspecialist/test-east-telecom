from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

# Language switcher endpoint
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

# Main URLs wrapped with language prefixes
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('quiz_app.urls')),  # your app's routes
)

# Static/media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
