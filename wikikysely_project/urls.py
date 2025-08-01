from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include
from wikikysely_project.survey.views import SurveyLoginView, survey_logout, login_redirect
from django.views.i18n import set_language

urlpatterns = [
    path('set-language/', set_language, name='set_language'),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('accounts/login/', SurveyLoginView.as_view(), name='login'),
    path('accounts/login-redirect/', login_redirect, name='login_redirect'),
    path('accounts/logout/', survey_logout, name='survey_logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('wikikysely_project.survey.urls')),
)

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
