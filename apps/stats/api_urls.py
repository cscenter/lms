from django.urls import include, path

app_name = 'stats-api'

urlpatterns = [
    path('v1/stats/', include([
        # TODO: move to appropriate app
        path('learning/', include('stats.learning.api_urls')),
        path('admission/', include('admission.api.stats.urls')),
    ]))
]
