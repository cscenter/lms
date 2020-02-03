from django.conf.urls import include, url

app_name = 'stats-api'

# TODO: separate and move to appropriate apps
urlpatterns = [
    url(r'^v1/stats/', include([
        url(r'^learning/', include('stats.learning.api_urls')),
        url(r'^admission/', include('stats.admission.api_urls')),
    ]))
]
