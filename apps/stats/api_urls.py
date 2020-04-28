from django.conf.urls import include, url

app_name = 'stats-api'

urlpatterns = [
    url(r'^v1/stats/', include([
        # TODO: move to appropriate app
        url(r'^learning/', include('stats.learning.api_urls')),
        url(r'^admission/', include('admission.api.stats.urls')),
    ]))
]
