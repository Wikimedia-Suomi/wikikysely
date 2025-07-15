from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include
from django.views.i18n import set_language

urlpatterns = [
    path('set-language/', set_language, name='set_language'),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('survey.urls')),
)

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
